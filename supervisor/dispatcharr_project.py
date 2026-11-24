"""Offline, bounded translator for separately authorized local monitoring exports.

No network, service clients, shell, configuration mutation or access to the Docker socket.
"""
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
import uuid

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_protocol import NS, PROJECTIONS, check, decode

INPUT = Path('/run/samwise-monitor-inputs')
OUTPUT = Path('/run/samwise-observations')
POLICY = Path('/etc/samwise/dispatcharr-evidence')
BOOT = Path('/proc/sys/kernel/random/boot_id')
CHANNEL = '67d9ed9926f9e1ef90002ff7dbfd790f'
CONTAINERS = {'backend':'dispatcharr', 'gateway':'rivendell-iptv-gateway',
              'vpn-container':'rivendell-iptv-vpn', 'jellyfin':'jellyfin'}
SOURCES = {name: PROJECTIONS[name][0] for name in CONTAINERS} | {
    'celery':'dispatcharr-pong-v1', 'protection':'kernel-policy-v1', 'livetv':'jellyfin-livetv-v1'}
LIMIT = 32768


def fields(obj, names):
    check(type(obj) is dict and set(obj) == set(names.split()))


def number(value):
    check(type(value) is int and 0 < value < 2**63)
    return value


def digest(value):
    check(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None)
    return value


def boolean(value):
    check(type(value) is bool)
    return value


@contextlib.contextmanager
def directory(path, owner, private=False):
    # Anchor every path component. Production paths have no writable/symlink ancestors.
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        check(path.is_absolute() and '..' not in path.parts)
        for part in path.parts[1:]:
            child = os.open(part, os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            # Sticky /tmp may contain a private fixture; production uses only /etc and /run.
            check(st.st_uid in (0, owner) and (not st.st_mode & 0o022 or
                  (st.st_uid == 0 and st.st_mode & stat.S_ISVTX and part == 'tmp')))
        check(os.fstat(fd).st_uid == owner and not os.fstat(fd).st_mode & 0o022)
        if private:
            check(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700)
        yield fd
    finally:
        os.close(fd)


def read_json(fd, name, owner):
    fd2 = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    with os.fdopen(fd2, 'rb') as stream:
        st = os.fstat(fd2)
        check(stat.S_ISREG(st.st_mode) and st.st_uid == owner and st.st_nlink == 1 and
              stat.S_IMODE(st.st_mode) in (0o400,0o440,0o600,0o640) and st.st_size <= LIMIT)
        data = stream.read(LIMIT + 1)
        end = os.stat(name, dir_fd=fd, follow_symlinks=False)
        check(os.path.samestat(st,end) and st.st_ctime_ns == end.st_ctime_ns and len(data)==st.st_size)
    return decode(data), st.st_mtime_ns


def snapshot(fd, name, owner, boot, now):
    obj, stamp = read_json(fd, name+'.json', owner)
    fields(obj,'source target boot_id sampled_ns evidence')
    check(obj['source'] == SOURCES[name] and obj['target'] == 'rivendell-dispatcharr' and obj['boot_id'] == boot)
    sample = number(obj['sampled_ns'])
    check(sample <= stamp <= now and type(obj['evidence']) is dict)
    return sample, obj['evidence']


def container(name, s, row):
    fields(row,'Name Id Status Running Pid StartedNs Health HealthEndNs HealthExitCode')
    check(row['Name'] == '/'+CONTAINERS[name])
    digest(row['Id'])
    running = boolean(row['Running'])
    check(type(row['Pid']) is int and row['Pid'] >= 0)
    if row['Status'] in ('exited','dead'):
        check(row['StartedNs'] is None or number(row['StartedNs']) <= s)
        check(not running and row['Pid'] == 0 and row['Health'] == 'none' and row['HealthEndNs'] is None)
        check(row['HealthExitCode'] is None)
        return s, 'stopped'
    check(row['Status'] == 'running' and running and row['Pid'] > 0)
    health = row['Health']
    check(health in ('healthy','unhealthy'))
    code = row['HealthExitCode']
    check(type(code) is int and 0 <= code <= 255 and (code == 0) == (health == 'healthy'))
    probe = number(row['HealthEndNs'])
    check(number(row['StartedNs']) <= probe <= s)
    return probe, 'running' if health == 'healthy' else 'unhealthy'


def celery(s, row, runtime):
    fields(row,'container_id event returncode count output_complete reply_output_valid default_present dvr_present')
    cs, c = runtime
    ct, cv = container('backend', cs, c)
    check(cv == 'running' and c['StartedNs'] <= s and digest(row['container_id']) == c['Id'])
    check(boolean(row['output_complete']) and boolean(row['reply_output_valid']))
    roles = int(boolean(row['default_present'])) + int(boolean(row['dvr_present']))
    check(type(row['count']) is int and row['count'] == roles and type(row['returncode']) is int)
    check(row['returncode'] == 0 and row['event'] == ('pass' if roles==2 else 'fail'))
    return min(s,ct), 'both-ready' if roles == 2 else 'readiness-failed'


def namespace(value):
    check(type(value) is list and len(value) == 2)
    return (number(value[0]), number(value[1]))


def protection(name, s, row, runtime, policy):
    fields(policy,'policy_sha256 rules_sha256')
    fields(row,'policy_sha256 rules_sha256 generation_before generation_after relay_generation grant_generation '
               'container_id host_ns owner_ns grant_ns backend_ns relay_ns tunnel_default output_drop '
               'dns_restricted ipv6_disabled')
    check(digest(row['generation_before']) == digest(row['generation_after']))
    # A missing/corrupt file is never translated to a withdrawal. Null is an explicit,
    # successfully sampled withdrawal accompanied by live rule and namespace evidence.
    grant = row['grant_generation']
    check((grant is None and row['grant_ns'] is None) or
          (digest(grant) == row['generation_before'] and namespace(row['grant_ns'])))
    relay_generation = digest(row['relay_generation'])
    matches = (digest(row['policy_sha256']) == digest(policy['policy_sha256']))
    matches &= (digest(row['rules_sha256']) == digest(policy['rules_sha256']))
    cs,c = runtime
    ct,cv = container('vpn-container',cs,c)
    check(cv == 'running' and c['StartedNs'] <= s and digest(row['container_id']) == c['Id'])
    host, owner, backend, relay = [namespace(row[k]) for k in ('host_ns','owner_ns','backend_ns','relay_ns')]
    checks = [boolean(row[k]) for k in ('tunnel_default','output_drop','dns_restricted','ipv6_disabled')]
    if not matches:
        value = 'failed'
    elif grant is None:
        value = 'withdrawn'
    elif relay_generation != grant or owner == host or namespace(row['grant_ns']) != owner or backend != owner or relay != owner:
        value = 'failed'
    elif name == 'vpn' and not all(checks):
        value = 'failed'
    else:
        value = 'verified'
    return min(s,ct), value


def instant(text):
    check(type(text) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?Z', text))
    # Jellyfin timestamps can have a seventh fractional digit (100 ns).
    whole, _, fraction = text[:-1].partition('.')
    seconds = int(dt.datetime.fromisoformat(whole).replace(tzinfo=dt.timezone.utc).timestamp())
    return seconds*NS + int(fraction.ljust(9,'0'))


def livetv(name, s, row, runtime):
    fields(row,'container_id channel_id channels programs')
    cs, c = runtime
    ct, cv = container('jellyfin', cs, c)
    check(cv == 'running' and c['StartedNs'] <= s and digest(row['container_id']) == c['Id'])
    start = min(s, ct)
    expiry = ct + PROJECTIONS['jellyfin'][1] * NS
    check(row['channel_id'] == CHANNEL)
    channels = row['channels']
    fields(channels,'Items TotalRecordCount')
    items = channels['Items']
    check(type(items) is list and type(channels['TotalRecordCount']) is int and len(items)==channels['TotalRecordCount']<=1)
    if items:
        c=items[0]
        fields(c,'Id Name Number')
        check(c=={'Id':CHANNEL,'Number':'9001','Name':'DW English'})
    if not items and row['programs'] is not None:
        programs = row['programs']
        fields(programs, 'Items TotalRecordCount')
        check(programs['Items'] == [] and type(programs['TotalRecordCount']) is int
              and programs['TotalRecordCount'] == 0)
    if name=='jellyfin-channel':
        return start, 'present' if items else 'absent', expiry
    check(bool(items))
    programs=row['programs']
    fields(programs,'Items TotalRecordCount')
    listings=programs['Items']
    check(type(listings) is list and type(programs['TotalRecordCount']) is int and
          len(listings)==programs['TotalRecordCount']<=1)
    if not listings:
        return start, 'empty', expiry
    item=listings[0]
    fields(item,'ChannelId StartDate EndDate')
    end=instant(item['EndDate'])
    check(item['ChannelId']==CHANNEL and instant(item['StartDate']) <= s < end)
    return start, 'current', min(end, expiry)


def publish(fd, name, result):
    start, value, expiry = result
    source, ttl = PROJECTIONS[name]
    end = start + ttl * NS
    if expiry is not None:
        end = min(expiry, end)
    check(start < end)
    data = json.dumps(dict(schema='samwise-projection-v2', source=source, name=name,
                           sample_ns=start, until_ns=end, value=value)).encode()
    temp = '.dispatcharr-' + secrets.token_hex(16)
    dest = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=fd)
    try:
        with os.fdopen(dest, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), 0o640)
            os.utime(stream.fileno(), ns=(start, start))
        os.replace(temp, name, src_dir_fd=fd, dst_dir_fd=fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp, dir_fd=fd)


def project(source_dir, output_dir, policy_dir, owner, boot, now):
    check(str(uuid.UUID(boot)) == boot)
    samples = {}
    policy = None
    with contextlib.suppress(OSError, ValueError):
        with directory(source_dir, owner, private=True) as fd:
            for topic in SOURCES:
                with contextlib.suppress(OSError, ValueError):
                    samples[topic] = snapshot(fd, topic, owner, boot, now)
    with contextlib.suppress(OSError, ValueError):
        with directory(policy_dir, owner, private=True) as fd:
            policy, _ = read_json(fd, 'enrollment.json', owner)
    with directory(output_dir, owner) as fd:
        for name in PROJECTIONS:
            if name == 'celery':
                continue  # Exclusive leased publisher; never write or unlink it here.
            try:
                if name in CONTAINERS:
                    result = (*container(name, *samples[name]), None)
                elif name in ('guard', 'vpn'):
                    result = (*protection(name, *samples['protection'], samples['vpn-container'], policy), None)
                else:
                    result = livetv(name, *samples['livetv'], samples['jellyfin'])
                publish(fd, name, result)
            except (ValueError, KeyError, TypeError, OSError, OverflowError):
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=fd)


if __name__ == '__main__':
    try:
        project(INPUT, OUTPUT, POLICY, 0, BOOT.read_text().strip(), time.time_ns())
    except (ValueError, OSError):
        sys.exit(1)
