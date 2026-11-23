"""Field selectors for an authorized monitoring custodian working on existing captures.

No I/O. Inputs stay private. Only the returned fields belong in a monitor export.
The custodian must supply the authenticated source, original sample time and boot.
"""
import datetime as dt
import hashlib
import json
import re

from ops_protocol import NS, check
from dispatcharr_project import CHANNEL


def engine_time(value):
    # Docker uses RFC3339Nano with a zone. Preserve fractional nanoseconds.
    check(type(value) is str)
    match = re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?(Z|[+-]\d\d:\d\d)', value)
    check(match)
    second = dt.datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00'))
    return int(second.timestamp()) * NS + int((match[2] or '').ljust(9,'0'))


def engine_fields(inspect):
    state = inspect['State']
    row = dict(Name=inspect['Name'], Id=inspect['Id'], Status=state['Status'],
               Running=state['Running'], Pid=state['Pid'], StartedNs=None,
               Health='none', HealthEndNs=None, HealthExitCode=None)
    if row['Status'] == 'running':
        h = state['Health']
        log = h['Log'][-1]
        row.update(StartedNs=engine_time(state['StartedAt']), Health=h['Status'],
                   HealthEndNs=engine_time(log['End']), HealthExitCode=log['ExitCode'])
    return row


def celery_fields(container_id, validated_terminal):
    # Caller validates the *whole* original receipt with its pinned lifecycle reader.
    check(validated_terminal['stage'] == 'celery' and validated_terminal['event'] in ('pass','fail'))
    keys = ('event','returncode','count','output_complete','reply_output_valid','default_present','dvr_present')
    return dict(container_id=container_id, **{k:validated_terminal[k] for k in keys})


def page(raw, keys):
    items = raw['Items']
    count = raw['TotalRecordCount']
    check(type(items) is list and type(count) is int and 0 <= count == len(items) <= 1)
    return dict(Items=[{k:item[k] for k in keys} for item in items], TotalRecordCount=count)


def rules_digest(canonical_table):
    # Both sides use the pinned permanent-streaming/contracts.py canonical() function.
    # Provision the expected digest from canonical(expected_table(enrolled_policy)).
    data = json.dumps(canonical_table, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def channel_page(raw):
    # An incomplete or unbounded inventory cannot establish absence.
    items, count = raw['Items'], raw['TotalRecordCount']
    check(type(items) is list and type(count) is int and 0 <= len(items) == count <= 4096)
    selected = []
    for item in items:
        channel_id, name, number = item['Id'], item['Name'], item['Number']
        check(all(type(field) is str for field in (channel_id, name, number)))
        if channel_id == CHANNEL or number == '9001' or name == 'DW English':
            check((channel_id, name, number) == (CHANNEL, 'DW English', '9001'))
            selected.append(dict(Id=channel_id, Name=name, Number=number))
    check(len(selected) <= 1)
    return dict(Items=selected, TotalRecordCount=len(selected))


def livetv_fields(container_id, queried_id, channels, programs):
    # Inputs are complete responses to the authenticated channel-ID and current-program queries.
    check(queried_id == CHANNEL)
    return dict(container_id=container_id,channel_id=queried_id,
                channels=channel_page(channels),
                programs=None if programs is None else page(programs, ('ChannelId','StartDate','EndDate')))
