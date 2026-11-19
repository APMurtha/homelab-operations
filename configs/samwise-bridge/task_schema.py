"""Strict task-envelope validation for future Samwise repository work.

This module is intentionally NOT wired into the running worker. A validated
request is data, not authorization to execute. No shell commands or prompts
are accepted from GitHub issue content.
"""
import hashlib
import json
import re
from dataclasses import dataclass

PREFIX = "samwise-task-v2:"
ALLOWED = frozenset({"repo-inventory"})
REVISION = 1
MAX_BYTES = 2048
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class InvalidTask(ValueError):
    pass


@dataclass(frozen=True)
class Task:
    kind: str
    revision: int
    commit: str
    digest: str


def parse(body: str) -> Task:
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BYTES:
        raise InvalidTask("invalid task size")
    if not body.startswith(PREFIX):
        raise InvalidTask("missing v2 prefix")
    payload = body[len(PREFIX):].strip()
    try:
        value = json.loads(payload)
    except (ValueError, TypeError) as exc:
        raise InvalidTask("invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"kind", "revision", "commit"}:
        raise InvalidTask("unknown or missing fields")
    kind, revision, commit = value["kind"], value["revision"], value["commit"]
    if kind not in ALLOWED or type(revision) is not int or revision != REVISION:
        raise InvalidTask("unsupported task kind or revision")
    if not isinstance(commit, str) or not GIT_SHA.fullmatch(commit):
        raise InvalidTask("commit must be a pinned Git commit SHA")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    return Task(kind, revision, commit, digest)


def same_authorized_content(body: str, authorized_digest: str) -> bool:
    """Use only after verifying owner identity and owner-authored approval event.

    Store the digest from the approved issue body, then recheck before work.
    This alone does not make a task safe to execute.
    """
    try:
        return parse(body).digest == authorized_digest
    except InvalidTask:
        return False
