import re

_IPV4_CIDR_RE = re.compile(
    r"^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}"
    r"/(?:3[0-2]|[12]?\d)$"
)


def is_valid_ipv4_cidr(value) -> bool:
    if not isinstance(value, str):
        return False
    return _IPV4_CIDR_RE.fullmatch(value) is not None
