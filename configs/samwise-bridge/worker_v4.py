"""One explicitly selected V4 GitHub issue. Dedicated state; no polling or service installer."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

import evidence_v4 as evidence
import publisher
from worker import BridgeError, OWNER, REPO, gh
from worker_v2 import REPO_ID

STATE = Path.home() / ".local/state/samwise-dispatcharr-v4"
READY = "samwise:v4-ready"
QUERY = """
query($number:Int!){
  viewer { databaseId }
  repository(owner:"APMurtha",name:"homelab-operations"){
    databaseId
    ref(qualifiedName:"refs/heads/main"){target{oid}}
    issue(number:$number){
      number state body lastEditedAt author{... on User{databaseId}}
      labels(first:100){nodes{name} pageInfo{hasNextPage}}
      timelineItems(last:1,itemTypes:[LABELED_EVENT,UNLABELED_EVENT]){nodes{
        __typename ... on LabeledEvent{id createdAt label{name} actor{... on User{databaseId}}}
      }}
      comments(last:1){nodes{id createdAt lastEditedAt body author{... on User{databaseId}}}}
    }
  }
}
"""


def approval(number):
    response = gh("graphql", "-f", "query=" + QUERY, "-F", f"number={number}")
    if response.get("errors"):
        raise BridgeError("GitHub authorization unavailable")
    data = response["data"]
    repo = data["repository"]
    if data["viewer"]["databaseId"] != OWNER or repo["databaseId"] != REPO_ID:
        raise BridgeError("controller identity mismatch")
    issue = repo["issue"]
    if not issue or issue["number"] != number or issue["state"] != "OPEN" or issue["lastEditedAt"]:
        return None
    if (issue["author"] or {}).get("databaseId") != OWNER:
        return None
    body = issue["body"]
    match = re.fullmatch(r"samwise-task-v4: dispatcharr-evidence-v1 ([0-9a-f]{40})", body)
    if not match or match[1] != repo["ref"]["target"]["oid"]:
        return None
    labels = issue["labels"]
    if labels["pageInfo"]["hasNextPage"] or READY not in [label["name"] for label in labels["nodes"]]:
        return None
    events = issue["timelineItems"]["nodes"]
    comments = issue["comments"]["nodes"]
    if not events or not comments:
        return None
    event, comment = events[-1], comments[-1]
    digest = hashlib.sha256(body.encode()).hexdigest()
    if (event["__typename"] != "LabeledEvent" or event["label"]["name"] != READY
            or (event["actor"] or {}).get("databaseId") != OWNER
            or (comment["author"] or {}).get("databaseId") != OWNER or comment["lastEditedAt"]
            or comment["createdAt"] < event["createdAt"]
            or comment["body"] != f"samwise-approve-v4: {event['id']} {digest}"):
        return None
    return match[1], digest, event["id"], comment["id"]


def run(db, number):
    if type(number) is not int or not 0 < number < 2**31:
        raise ValueError("invalid issue number")
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        issue INTEGER PRIMARY KEY, approval TEXT, image TEXT, started TEXT,
        status TEXT, report_hash TEXT, draft INTEGER)""")
    authorized = approval(number)
    if authorized is None:
        return False
    commit = authorized[0]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db:
        claim = db.execute("INSERT INTO jobs VALUES (?,?,?,?,'claimed',NULL,NULL) ON CONFLICT(issue) DO NOTHING",
                           (number, json.dumps(authorized), evidence.IMAGE, stamp))
    if not claim.rowcount:
        return False
    status, fingerprint, draft = "failed", None, None
    try:
        blobs = evidence.snapshot(commit)
        if approval(number) != authorized:
            status = "cancelled"
            return False
        content = evidence.report(commit, blobs, evidence.isolated(blobs))
        fingerprint = hashlib.sha256(content.encode()).hexdigest()
        if approval(number) != authorized:
            status = "cancelled"
            return False
        status = "publication-uncertain"
        with db:
            db.execute("UPDATE jobs SET status=?,report_hash=? WHERE issue=?", (status, fingerprint, number))
        title = f"Inventory DW English evidence for #{number}"
        draft = publisher.publish_file(stamp, commit, evidence.TARGET, content,
                                       f"samwise/v4/issue-{number}", title,
                                       f"Approved repository evidence inventory for #{number} at `{commit}`.",
                                       title, require_open_draft=True)
        status = "draft-created"
        return True
    finally:
        with db:
            db.execute("UPDATE jobs SET status=?,report_hash=?,draft=? WHERE issue=?",
                       (status, fingerprint, draft, number))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, type=int)
    args = parser.parse_args()
    os.umask(0o077)
    if os.geteuid() == 0:
        parser.error("dedicated unprivileged account required")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = STATE.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        parser.error("private V4 state required")
    with closing(sqlite3.connect(STATE / "jobs.sqlite3")) as ledger:
        raise SystemExit(0 if run(ledger, args.issue) else 1)
