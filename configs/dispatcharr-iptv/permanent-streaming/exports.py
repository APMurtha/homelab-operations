"""Atomic local-only one-channel exports; explicitly labeled renewable placeholder."""
import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import shutil
import uuid
from files import atomic, write_json

TVG_ID = 'dw-english-permanent'
NAME = 'DW English'
PLACEHOLDER = 'DW English live stream — placeholder, not a programme schedule'


def documents(channel_uuid, now):
    channel_uuid = str(uuid.UUID(channel_uuid))
    now = now.astimezone(dt.timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=1)
    end = start + dt.timedelta(hours=49)
    m3u = (f'#EXTM3U\n#EXTINF:-1 tvg-id="{TVG_ID}" tvg-name="{NAME}" '
           f'tvg-chno="9001",{NAME}\n'
           f'http://10.10.20.30:9191/proxy/ts/stream/{channel_uuid}\n').encode()
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<tv>'
           f'<channel id="{TVG_ID}"><display-name>{NAME}</display-name></channel>'
           f'<programme channel="{TVG_ID}" start="{start:%Y%m%d%H%M%S} +0000" '
           f'stop="{end:%Y%m%d%H%M%S} +0000"><title>{PLACEHOLDER}</title>'
           '<desc>Automatically refreshed availability placeholder. No broadcaster '
           'programme titles or schedule are supplied.</desc></programme></tv>\n').encode()
    return m3u, xml


def publish(root, channel_uuid, now=None):
    """Generation symlink commits the pair together; retain only two owned versions."""
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('export_directory_required')
    m3u, xml = documents(channel_uuid, now or dt.datetime.now(dt.timezone.utc))
    generation = 'g-' + hashlib.sha256(m3u + xml).hexdigest()[:24]
    target = root / generation
    if target.is_symlink(): raise ValueError('unsafe_generation')
    target.mkdir(mode=0o750, exist_ok=True)
    atomic(target / 'dispatcharr.m3u', m3u, 0o640)
    atomic(target / 'guide.xml', xml, 0o640)
    link = root / 'next'
    if link.exists() or link.is_symlink():
        if not link.is_symlink(): raise ValueError('unsafe_export_link')
        link.unlink()
    link.symlink_to(generation, target_is_directory=True)
    if (root / 'current').exists() and not (root / 'current').is_symlink():
        raise ValueError('unsafe_current_link')
    os.replace(link, root / 'current')
    old = sorted((p for p in root.iterdir() if re.fullmatch(r'g-[a-f0-9]{24}', p.name)
                  and p.name != generation), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in old[1:]:
        if p.is_symlink(): raise ValueError('unsafe_generation')
        shutil.rmtree(p)
    return {'generation': generation, 'channel_uuid': channel_uuid}
