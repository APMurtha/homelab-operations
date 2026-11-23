#!/usr/bin/env python3
"""Opt-in Bag-End worker with digest-bound offline repository inventory."""
from functools import partial
import json
import os
import subprocess

import publisher
import runner
from task_schema import GIT_SHA, InvalidTask, parse
import worker as fixture

REPO = fixture.REPO
OWNER = fixture.OWNER
REPO_ID = 1126036330


def authorization(number, *, claimed=False):
    path = f"{REPO}/issues/{number}"

    def candidate(issue):
        names = fixture.labels(issue)
        return (
            issue["number"] == number and issue["state"] == "open"
            and "pull_request" not in issue and (issue.get("user") or {}).get("id") == OWNER
            and fixture.READY in names and (fixture.RUNNING in names) == claimed
            and not names.intersection({fixture.DONE, fixture.FAILED})
        )

    issue = fixture.gh(path)
    if not candidate(issue):
        return None
    try:
        task = parse(issue.get("body"))
    except InvalidTask:
        return None
    events = list(publisher.pages(f"{path}/events"))
    ready = next((event for event in reversed(events)
                  if (event.get("label") or {}).get("name") == fixture.READY), None)
    if (not ready or ready["event"] != "labeled"
            or (ready.get("actor") or {}).get("id") != OWNER or type(ready["id"]) is not int):
        return None
    expected = f"samwise-approve-v2: {ready['id']} {task.digest}"
    comments = list(publisher.pages(f"{path}/comments"))
    approvals = [
        comment for comment in comments
        if (comment.get("user") or {}).get("id") == OWNER and comment["body"] == expected
        and comment["created_at"] == comment["updated_at"]
        and comment["created_at"] >= ready["created_at"]
    ]
    current = fixture.gh(path)
    if (len(approvals) != 1 or not candidate(current)
            or current["body"] != issue["body"] or current["updated_at"] != issue["updated_at"]):
        return None
    return task, ready["id"], approvals[0]["id"]


def verify_source(number, task):
    # GitHub supplies the current main tip. Verify ancestry locally without
    # fetching from, or trusting the remotes configured in, the checkout.
    ref = fixture.gh(f"{REPO}/git/ref/heads/{publisher.BASE}")
    tip = ref["object"]["sha"]
    if ref["object"]["type"] != "commit" or not GIT_SHA.fullmatch(tip):
        raise fixture.BridgeError("invalid GitHub base commit")
    options = dict(env=runner.ENV, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdout=subprocess.PIPE, timeout=15, check=True)
    try:
        subprocess.run(runner.git("merge-base", "--is-ancestor", task.commit, tip), **options)
        path = f"samwise-results/issue-{number}.json"
        directory = subprocess.run(runner.git("ls-tree", task.commit, "--", "samwise-results"),
                                   **options).stdout
        if directory:
            # Existing report directories are fine, but replacing a file/symlink
            # in their place or overwriting an existing report is forbidden.
            if not directory.startswith(b"040000 tree ") or subprocess.run(
                runner.git("ls-tree", task.commit, "--", path), **options
            ).stdout:
                raise fixture.BridgeError("result path already exists")
    except (OSError, subprocess.SubprocessError) as exc:
        raise fixture.BridgeError("pinned commit is unavailable or outside GitHub main") from exc


def recover(db):
    pending = db.execute(
        "SELECT issue, result, updated, report FROM receipts JOIN v2 USING(issue) "
        "WHERE published=0 ORDER BY issue"
    ).fetchall()
    for number, result, updated, report in pending:
        if result == "claimed":
            result = "interrupted"
            fixture.record(db, number, result)
        publisher.publish(db, number, result, updated, report)


def cycle(db, only_issue, *, image):
    if fixture.gh("user")["id"] != OWNER or fixture.gh(REPO)["id"] != REPO_ID:
        raise fixture.BridgeError("GitHub account or repository identity mismatch")
    db.execute("CREATE TABLE IF NOT EXISTS v2 (issue INTEGER PRIMARY KEY, "
               "digest TEXT NOT NULL, commit_sha TEXT NOT NULL, ready_event INTEGER NOT NULL, "
               "approval INTEGER NOT NULL, image TEXT NOT NULL, report TEXT)")
    db.commit()
    recover(db)
    candidates = ([{"number": only_issue}] if only_issue else
                  fixture.gh(f"{REPO}/issues?state=open&labels={fixture.READY}&per_page=100"))
    for candidate in candidates:
        number = candidate["number"]
        if type(number) is not int or number < 1:
            continue
        if db.execute("SELECT 1 FROM receipts WHERE issue=?", (number,)).fetchone():
            continue
        try:
            approved = authorization(number)
        except fixture.BridgeError as exc:
            if str(exc) == "GitHub history exceeds its review limit":
                continue
            raise
        if approved is None:
            continue
        task, ready, approval = approved
        stamp = fixture.datetime.now(fixture.timezone.utc).isoformat(timespec="seconds")
        with db:
            db.execute("INSERT INTO receipts VALUES (?, 'claimed', ?, 0)", (number, stamp))
            db.execute("INSERT INTO v2 VALUES (?, ?, ?, ?, ?, ?, NULL)",
                       (number, task.digest, task.commit, ready, approval, image))
        fixture.label(number, fixture.RUNNING)
        result = "cancelled"
        report = None
        if authorization(number, claimed=True) == approved:
            try:
                verify_source(number, task)
                # Revalidate after source checks, immediately before launching the job.
                if authorization(number, claimed=True) == approved:
                    data = runner.inventory(task, image)
                    report = json.dumps({
                        "issue": number, "kind": task.kind, "revision": task.revision,
                        "commit": task.commit, "digest": task.digest, "ready_event": ready,
                        "approval_comment": approval, "runner_image": image, "inventory": data,
                    })
                    result = "passed"
            except fixture.BridgeError as exc:
                print(f"Issue #{number}: {exc}", flush=True)
                result = "runner-failed"
        with db:
            db.execute("UPDATE receipts SET result=? WHERE issue=?", (result, number))
            db.execute("UPDATE v2 SET report=? WHERE issue=?", (report, number))
        publisher.publish(db, number, result, stamp, report)
        return result == "passed"
    return fixture.cycle(db, only_issue)


def main():
    image = os.environ.get("SAMWISE_RUNNER_IMAGE", "")
    if not runner.IMAGE_ID.fullmatch(image) or os.geteuid() == 0:
        raise SystemExit("Set SAMWISE_RUNNER_IMAGE to a reviewed local image ID and run rootless.")
    return fixture.main(partial(cycle, image=image))


if __name__ == "__main__":
    raise SystemExit(main())
