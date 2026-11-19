"""Strict task-envelope validation. Authorization is checked separately."""
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


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidTask("duplicate JSON field")
        result[key] = value
    return result


def parse(body: str) -> Task:
    if not isinstance(body, str) or len(body) > MAX_BYTES:
        raise InvalidTask("invalid task size")
    try:
        raw = body.encode("utf-8")
    except UnicodeError as exc:
        raise InvalidTask("invalid UTF-8") from exc
    if len(raw) > MAX_BYTES:
        raise InvalidTask("invalid task size")
    if not body.startswith(PREFIX):
        raise InvalidTask("missing v2 prefix")
    payload = body[len(PREFIX):].strip()
    try:
        value = json.loads(payload, object_pairs_hook=unique_fields)
    except (ValueError, RecursionError) as exc:
        raise InvalidTask("invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"kind", "revision", "commit"}:
        raise InvalidTask("unknown or missing fields")
    kind, revision, commit = value["kind"], value["revision"], value["commit"]
    if not isinstance(kind, str) or kind not in ALLOWED:
        raise InvalidTask("unsupported task kind")
    if type(revision) is not int or revision != REVISION:
        raise InvalidTask("unsupported task kind or revision")
    if not isinstance(commit, str) or not GIT_SHA.fullmatch(commit):
        raise InvalidTask("commit must be a pinned Git commit SHA")
    digest = hashlib.sha256(raw).hexdigest()
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
