"""Trusted GitHub publication. Model data can only fill the report fields."""
import json
import tempfile
from urllib.parse import urlencode

from worker import BridgeError, DONE, FAILED, OWNER, READY, REPO, RUNNING, gh, label, labels

BASE = "main"


def post(path, data):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as request:
        json.dump(data, request)
        request.flush()
        return gh(path, "-X", "POST", "--input", request.name)


def pages(path):
    for page in range(1, 4):
        items = gh(f"{path}?per_page=100&page={page}")
        yield from items
        if len(items) < 100:
            return
    raise BridgeError("GitHub history exceeds its review limit")


def publish_report(number, updated, report):
    path = f"samwise-results/issue-{number}.json"
    content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    return publish_file(updated, report["commit"], path, content,
                        f"samwise/results/issue-{number}", f"Samwise inventory for issue #{number}",
                        f"Proposed repository inventory for #{number}.",
                        f"Record Samwise inventory for issue #{number}")


def publish_file(updated, source_commit, path, content, branch, title, body, message,
                 *, require_open_draft=False):
    target = f"{REPO}/git"
    base = gh(f"{target}/commits/{source_commit}")
    tree = post(f"{target}/trees", {
        "base_tree": base["tree"]["sha"],
        "tree": [{"path": path, "mode": "100644", "type": "blob", "content": content}],
    })
    identity = {"name": "Samwise Bridge", "email": f"{OWNER}+APMurtha@users.noreply.github.com",
                "date": updated}
    commit = post(f"{target}/commits", {
        "message": message,
        "tree": tree["sha"], "parents": [source_commit],
        "author": identity, "committer": identity,
    })["sha"]
    query = urlencode({"state": "all", "head": f"APMurtha:{branch}", "base": BASE})
    matches = gh(f"{REPO}/pulls?{query}")
    if len(matches) > 1:
        raise BridgeError("ambiguous result pull request")
    if matches:
        pr = matches[0]
    else:
        try:
            ref = post(f"{target}/refs", {"ref": f"refs/heads/{branch}", "sha": commit})
        except BridgeError:
            ref = gh(f"{target}/ref/heads/{branch}")
        if ref["ref"] != f"refs/heads/{branch}" or ref["object"]["sha"] != commit:
            raise BridgeError("result branch has an unexpected commit")
        pr = post(f"{REPO}/pulls", {
            "title": title, "head": branch, "base": BASE,
            "body": body, "draft": True,
        })
    if (pr["head"]["sha"] != commit or pr["head"]["ref"] != branch
            or pr["base"]["ref"] != BASE or pr["base"]["repo"]["id"] != 1126036330):
        raise BridgeError("result pull request has an unexpected revision")
    if require_open_draft and (pr.get("draft") is not True or pr.get("state") != "open"
                               or pr["head"]["repo"]["id"] != 1126036330):
        raise BridgeError("expected an open same-repository draft")
    if type(pr["number"]) is not int or pr["number"] < 1:
        raise BridgeError("invalid result pull request number")
    return pr["number"]


def publish(db, number, result, updated, report):
    summary = f"Samwise v2 result for #{number}: `{result}`."
    if result == "passed":
        pr = publish_report(number, updated, json.loads(report))
        summary += f" Proposed inventory: #{pr}."
    finish(db, number, result, summary, "v2")


def finish(db, number, result, summary, version):
    path = f"{REPO}/issues/{number}"
    marker = f"<!-- samwise-{version}-receipt:{number} -->"
    body = f"{summary}\n\n{marker}"
    comments = list(pages(f"{path}/comments"))
    if not any(comment["user"]["id"] == OWNER and comment["body"] == body
               for comment in comments):
        post(f"{path}/comments", {"body": body})
    issue = gh(path)
    names = labels(issue)
    terminal = DONE if result == "passed" else FAILED
    if terminal not in names:
        label(number, terminal)
    for name in (READY, RUNNING):
        if name in names:
            label(number, name, remove=True)
    db.execute("UPDATE receipts SET published=1 WHERE issue=?", (number,))
    db.commit()
