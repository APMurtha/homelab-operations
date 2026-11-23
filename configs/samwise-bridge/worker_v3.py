#!/usr/bin/env python3
"""Companion poller for reviewed development templates. Own state and replay ledger."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import development
import development_job as job
import publisher
import worker
import worker_v2

STATE = Path.home() / ".local/state/samwise-development-v3"


def offer(path, approval, task, comments):
    body = (f"Review the addition of `{job.TARGET}` using template `{job.TEMPLATE}` "
            f"at `{task.commit}`. After reviewing this issue, the owner may post this exact "
            f"line as a new comment:\n\n```text\n{approval}\n```")
    if not any(c["user"]["id"] == worker.OWNER and c["body"] == body for c in comments):
        publisher.post(f"{path}/comments", {"body": body})


def authorization(number, claimed=False):
    approval = worker_v2.authorization(number, claimed=claimed, parse_task=development.parse,
                                       version="v3", offer=offer)
    if approval is None:
        return None
    # REST timestamps have one-second precision. GitHub's edit metadata also
    # catches a body edited and restored to its approved bytes.
    query = """query($issue:Int!, $comment:ID!) {
      repository(owner:"APMurtha", name:"homelab-operations") {
        issue(number:$issue) { state body lastEditedAt }
      }
      node(id:$comment) { ... on IssueComment { body lastEditedAt } }
    }"""
    task, event, comment_id = approval
    comment = worker.gh(f"{worker.REPO}/issues/comments/{comment_id}")
    data = worker.gh("graphql", "-f", f"query={query}", "-F", f"issue={number}",
                     "-f", f"comment={comment['node_id']}")["data"]
    issue = data["repository"]["issue"]
    current = data["node"]
    if (not issue or issue["state"] != "OPEN" or issue["lastEditedAt"] is not None
            or hashlib.sha256(issue["body"].encode()).hexdigest() != task.digest
            or not current or current["lastEditedAt"] is not None
            or current["body"] != f"samwise-approve-v3: {event} {task.digest}"):
        return None
    return approval


def publish(db, number, result, stamp, metadata, output):
    summary = f"Samwise v3 result for #{number}: `{result}`."
    if result == "passed":
        evidence = json.loads(metadata)
        data = job.validate(json.loads(output))
        evidence["test"] = data["test"]
        evidence["source_sha256"] = hashlib.sha256(data["source"].encode()).hexdigest()
        body = f"Development result for #{number}.\n\n```json\n{json.dumps(evidence, indent=2)}\n```"
        title = f"Add integer parity helper for #{number}"
        pr = publisher.publish_file(stamp, evidence["commit"], job.TARGET, data["source"],
                                    f"samwise/development/issue-{number}", title, body, title,
                                    require_open_draft=True)
        summary += f" Draft PR: #{pr}."
    publisher.finish(db, number, result, summary, "v3")


def cycle(db, only_issue):
    if worker.gh("user")["id"] != worker.OWNER or worker.gh(worker.REPO)["id"] != worker_v2.REPO_ID:
        raise worker.BridgeError("GitHub account or repository identity mismatch")
    db.execute("CREATE TABLE IF NOT EXISTS development (issue INTEGER PRIMARY KEY, "
               "metadata TEXT NOT NULL, output TEXT)")
    pending = db.execute("SELECT issue,result,updated,metadata,output FROM receipts "
                         "JOIN development USING(issue) WHERE published=0 ORDER BY issue").fetchall()
    for number, result, stamp, metadata, output in pending:
        if result == "claimed":
            result = "interrupted"
            worker.record(db, number, result)
        publish(db, number, result, stamp, metadata, output)

    queue = ([{"number": only_issue}] if only_issue else
             worker.gh(f"{worker.REPO}/issues?state=open&labels={worker.READY}&per_page=100"))
    for issue in queue:
        number = issue["number"]
        if type(number) is not int or number < 1:
            continue
        if db.execute("SELECT 1 FROM receipts WHERE issue=?", (number,)).fetchone():
            continue
        try:
            approval = authorization(number)
        except worker.BridgeError as exc:
            if str(exc) == "GitHub history exceeds its review limit":
                continue
            raise
        if approval is None:
            continue
        task, event, comment = approval
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        metadata = json.dumps(dict(issue=number, commit=task.commit, body_sha256=task.digest,
                                   ready_event=event, approval_comment=comment, template=task.kind,
                                   revision=task.revision, path=job.TARGET, image=development.IMAGE,
                                   runner_program_sha256=hashlib.sha256(
                                       Path(job.__file__).read_bytes()).hexdigest()))
        with db:
            db.execute("INSERT INTO receipts VALUES (?, 'claimed', ?, 0)", (number, stamp))
            db.execute("INSERT INTO development VALUES (?, ?, NULL)", (number, metadata))
        worker.label(number, worker.RUNNING)
        result, output = "cancelled", None
        if authorization(number, claimed=True) == approval:
            try:
                development.verify_base(task)
                if authorization(number, claimed=True) == approval:
                    data = development.develop(development.IMAGE)
                    development.verify_base(task)
                    if authorization(number, claimed=True) == approval:
                        output = json.dumps(data)
                        result = "passed"
            except worker.BridgeError as exc:
                print(f"Issue #{number}: {exc}", flush=True)
                result = "runner-failed"
        with db:
            db.execute("UPDATE development SET output=? WHERE issue=?", (output, number))
            db.execute("UPDATE receipts SET result=? WHERE issue=?", (result, number))
        publish(db, number, result, stamp, metadata, output)
        return result == "passed"
    return False


if __name__ == "__main__":
    worker.STATE = STATE
    raise SystemExit(worker.main(cycle))
