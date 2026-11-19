#!/usr/bin/env python3
"""Bag-End's opt-in GitHub Issues worker for a single read-only smoke task."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import sqlite3
import stat
import subprocess
import tempfile
import time

REPO = "repos/APMurtha/homelab-operations"
OWNER = 57697374
READY = "samwise:ready"
RUNNING = "samwise:running"
DONE = "samwise:done"
FAILED = "samwise:failed"
TASK = "samwise-task: fixture-count-v1"
PROMPT = (
    "Analyze this synthetic inventory only. Count entries marked ready: "
    "oak=ready, ash=waiting, elm=ready. Return only the count as a single digit."
)
STATE = Path.home() / ".local/state/samwise-codex"


class BridgeError(Exception):
    """An operator-safe error message."""


def gh(path, *args):
    # Use the already authenticated local GitHub CLI, without inherited token overrides.
    env = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin", "GH_PROMPT_DISABLED": "1"}
    try:
        result = subprocess.run(
            ["/usr/bin/gh", "api", "--hostname", "github.com", path, *args],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=25, check=True,
        )
        return json.loads(result.stdout) if result.stdout else None
    except (subprocess.SubprocessError, ValueError, OSError) as exc:
        raise BridgeError("GitHub API request failed") from exc


def label(number, name, *, remove=False):
    path = f"{REPO}/issues/{number}/labels"
    if remove:
        gh(f"{path}/{name}", "-X", "DELETE")
    else:
        gh(path, "-X", "POST", "-f", f"labels[]={name}")


def labels(issue):
    return {item["name"] for item in issue["labels"]}


def eligible(issue):
    return (
        issue["state"] == "open" and "pull_request" not in issue
        and (issue.get("user") or {}).get("id") == OWNER
        and (issue.get("body") or "").strip() == TASK
        and READY in labels(issue)
        and not labels(issue).intersection({RUNNING, DONE, FAILED})
    )


def owner_approved(number):
    # The most recent ready-label event must be an addition by the owner.
    # An oversized event history is ineligible rather than partially trusted.
    latest = None
    for page in range(1, 4):
        events = gh(f"{REPO}/issues/{number}/events?per_page=100&page={page}")
        for event in events:
            if (event.get("label") or {}).get("name") == READY:
                latest = event
        if len(events) < 100:
            return bool(latest and latest["event"] == "labeled"
                        and (latest.get("actor") or {}).get("id") == OWNER)
    return False


def codex_task():
    # Codex receives only the fixed synthetic fixture. No checkout, issue text,
    # GitHub credentials, service environment, or model output crosses the boundary.
    with tempfile.TemporaryDirectory(prefix="codex-", dir=STATE) as directory:
        answer = Path(directory) / "answer"
        env = {
            "HOME": str(Path.home()), "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8", "TMPDIR": directory,
        }
        command = [
            "/usr/local/bin/codex", "--ask-for-approval", "never", "exec",
            "--sandbox", "read-only", "--ephemeral", "--ignore-user-config",
            "--ignore-rules", "--skip-git-repo-check", "--disable", "shell_tool",
            "--disable", "plugins", "--disable", "hooks", "--disable", "multi_agent",
            "--disable", "apps", "--disable", "shell_snapshot",
            "--enable", "skip_host_skill_discovery", "-c", 'web_search="disabled"',
            "--output-last-message", str(answer), "-",
        ]
        try:
            with subprocess.Popen(
                command, cwd=directory, env=env, start_new_session=True,
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            ) as process:
                try:
                    process.communicate(PROMPT.encode(), timeout=90)
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                if process.returncode != 0:
                    return "codex-error"
            with answer.open("rb") as output:
                return "passed" if output.read(32).strip() == b"2" else "unexpected-output"
        except subprocess.TimeoutExpired:
            return "timeout"
        except OSError:
            return "codex-error"


def record(db, number, result):
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.execute("UPDATE receipts SET result=?, updated=? WHERE issue=?",
               (result, timestamp, number))
    db.commit()


def publish(db, number, result):
    issue = gh(f"{REPO}/issues/{number}")
    if issue["state"] == "open":
        names = labels(issue)
        terminal = DONE if result == "passed" else FAILED
        if terminal not in names:
            label(number, terminal)
        for name in (READY, RUNNING):
            if name in names:
                label(number, name, remove=True)
    db.execute("UPDATE receipts SET published=1 WHERE issue=?", (number,))
    db.commit()


def recover(db):
    for number, result in db.execute(
        "SELECT issue, result FROM receipts WHERE published=0 ORDER BY issue"
    ).fetchall():
        if result == "claimed":
            result = "interrupted"
            record(db, number, result)
        publish(db, number, result)


def cycle(db, only_issue):
    if gh("user")["id"] != OWNER or gh(REPO)["id"] != 1126036330:
        raise BridgeError("GitHub account or repository identity mismatch")
    recover(db)
    if only_issue:
        candidates = [{"number": only_issue}]
    else:
        candidates = gh(f"{REPO}/issues?state=open&labels={READY}&per_page=100")
    for candidate in candidates:
        number = candidate["number"]
        if db.execute("SELECT 1 FROM receipts WHERE issue=?", (number,)).fetchone():
            continue
        issue_path = f"{REPO}/issues/{number}"
        issue = gh(issue_path)
        if not eligible(issue) or not owner_approved(number):
            continue
        # Re-read after checking actors to catch edits/cancellation during the checks.
        current = gh(issue_path)
        if not eligible(current) or current["updated_at"] != issue["updated_at"]:
            continue
        db.execute("INSERT INTO receipts VALUES (?, 'claimed', ?, 0)",
                   (number, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        db.commit()
        label(number, RUNNING)
        current = gh(issue_path)
        # A last read before starting also catches withdrawal during the claim.
        claimed = RUNNING in labels(current)
        current["labels"] = [item for item in current["labels"] if item["name"] != RUNNING]
        result = "cancelled"
        if claimed and eligible(current) and owner_approved(number):
            result = codex_task()
        record(db, number, result)
        publish(db, number, result)
        print(f"Issue #{number}: {result}", flush=True)
        return result == "passed"
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--poll", action="store_true")
    parser.add_argument("--issue", type=int, help="Process only this issue in --once mode")
    args = parser.parse_args()
    if args.issue is not None and (not args.once or args.issue < 1):
        parser.error("--issue requires --once and a positive issue number")
    if os.uname().nodename.lower() != "bag-end":
        parser.error("This worker is pinned to Bag-End")
    os.umask(0o077)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = STATE.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        parser.error("Worker state must be an owner-only directory")
    with (STATE / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another worker holds the local lock")
        with closing(sqlite3.connect(STATE / "receipts.sqlite3")) as db:
            db.execute("CREATE TABLE IF NOT EXISTS receipts (issue INTEGER PRIMARY KEY, "
                       "result TEXT NOT NULL, updated TEXT NOT NULL, published INTEGER NOT NULL)")
            db.commit()
            while True:
                try:
                    passed = cycle(db, args.issue)
                    if args.once:
                        return int(bool(args.issue) and not passed)
                except BridgeError as exc:
                    print(str(exc), flush=True)
                    if args.once:
                        return 1
                time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
