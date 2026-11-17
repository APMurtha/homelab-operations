"""No media request: correlate current relay, committed API identity and export pair."""
from pathlib import Path
from files import read_json
from health import current


def verify(runtime='/runtime', state='/data/permanent-streaming'):
    record=current(runtime); runtime=Path(runtime)
    binding=read_json(runtime/'binding.json'); exported=read_json(runtime/'export-state.json')
    owned=read_json(Path(state)/'owned.json')
    if (Path(state)/'journal.json').exists() or (Path(state)/'commit.json').exists():
        raise ValueError('registration_pending')
    if binding['instance'] != record['instance'] or exported['instance'] != record['instance']:
        raise ValueError('stale_binding')
    if binding['channel_uuid'] != owned['channel']['uuid'] or exported['channel_uuid'] != binding['channel_uuid']:
        raise ValueError('export_binding_mismatch')
    if owned['stream']['url'] != record['endpoint']:
        raise ValueError('stale_stream')


if __name__=='__main__':
    try: verify()
    except Exception: raise SystemExit('Binding/export verification failed; details withheld.')
