"""Managed wrapper: fresh identity, bounded telemetry, hourly exports, signal cleanup."""
import datetime as dt
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from exports import publish
from files import private_json, read_json, write_json
from hls_relay import Relay, server


def run(config, runtime=Path('/runtime'), export_root=Path('/exports')):
    runtime = Path(runtime)
    if not runtime.is_dir() or runtime.is_symlink():
        raise ValueError('runtime_directory_required')
    for name in ['endpoint.json', 'stats.json', 'export-state.json', 'events.jsonl', 'events.jsonl.1']:
        p = runtime / name
        if p.is_symlink(): raise ValueError('unsafe_runtime_file')
        p.unlink(missing_ok=True)
    if set(config) != {'source', 'guard_status_dir', 'ready_hash', 'manifest_deadline_seconds', 'segment_deadline_seconds'}:
        raise ValueError('unexpected_configuration')
    if config['manifest_deadline_seconds'] != 12 or config['segment_deadline_seconds'] != 12:
        raise ValueError('deadline_contract_changed')
    config = dict(config, state_dir=str(runtime), telemetry_path=str(runtime / 'events.jsonl'))
    relay = Relay(config)
    relay.check()
    srv = server(relay)
    stopped = threading.Event()
    def stop(*_):
        if not stopped.is_set():
            stopped.set()
            threading.Thread(target=srv.shutdown, daemon=True).start()
    for sig in [signal.SIGTERM, signal.SIGINT]: signal.signal(sig, stop)
    record = {'instance': relay.session, 'endpoint': f'http://127.0.0.1:19193/s/{relay.session}/live.m3u8'}
    write_json(runtime / 'endpoint.json', record)
    def snapshots():
        generation = None
        while not stopped.is_set():
            try:
                relay.check()
                telemetry = relay.telemetry.snapshot()
                if telemetry['errors'] or telemetry['dropped']:
                    raise ValueError('telemetry_failure')
                binding = runtime / 'binding.json'
                if binding.exists():
                    registered = read_json(binding)
                    if registered['instance'] == relay.session:
                        hour = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H')
                        key = (registered['channel_uuid'], hour)
                        if generation != key:
                            exported = publish(export_root, registered['channel_uuid'])
                            write_json(runtime / 'export-state.json', dict(exported, instance=relay.session))
                            generation = key
                state = relay.snapshot()
                state.update(instance=relay.session, monotonic=time.monotonic(), stopped=False)
                write_json(runtime / 'stats.json', state)
            except Exception:
                relay.fatal = relay.fatal or 'operational_limit'
                stop()
                break
            if stopped.wait(2): break
    writer = threading.Thread(target=snapshots, name='relay-state', daemon=True)
    writer.start()
    try:
        srv.serve_forever(poll_interval=.1)
    finally:
        stopped.set()
        clean = relay.close()
        srv.server_close()
        writer.join(4)
        write_json(runtime / 'stats.json', {'instance': relay.session, 'monotonic': time.monotonic(),
                   'fatal': relay.fatal, 'stopped': True, 'clean_shutdown': clean and not writer.is_alive()})
        (runtime / 'endpoint.json').unlink(missing_ok=True)
    return 1 if relay.fatal or not clean or writer.is_alive() else 0


if __name__ == '__main__':
    try:
        os.umask(0o077)
        raise SystemExit(run(private_json('/run/credentials/relay.json')))
    except Exception:
        raise SystemExit('Relay refused; private details withheld.')
