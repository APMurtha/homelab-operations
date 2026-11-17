"""Private draft preparation and explicitly offline native API simulation."""
import argparse
import contextlib
import getpass
import json
import os
from pathlib import Path
import sys
import warnings
from .core import (OWNER, Refused, Redactor, Store, Dispatcharr, MetadataHTTPS,
                   catalogue, decode, digest, discover, plan, private_read, provider, select)

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('invalid_arguments_no_credentials_in_arguments')


def read_fixture(path):
    try:
        p = Path(path)
        if p.is_symlink() or not p.is_file(): raise Refused('fixture_file_required')
        with p.open('rb') as f: return decode(f.read(16 * 1024 * 1024 + 1))
    except OSError: raise Refused('fixture_unavailable') from None


def emit(value, redactor=None):
    redactor = redactor or Redactor()
    def clean(v):
        if isinstance(v, str): return redactor.text(v)
        if isinstance(v, list): return [clean(x) for x in v]
        if isinstance(v, dict): return {str(k):clean(x) for k,x in v.items()}
        return v
    print(json.dumps(clean(value), indent=2, ensure_ascii=True, allow_nan=False))


def summary(bundle):
    return {'key': bundle['provider']['key'], 'name': bundle['provider']['name'],
            'ownership': OWNER, 'status': 'PRIVATE DRAFT, NOT REGISTERED',
            'selected_channel_count': len(bundle['plan']['selected']),
            'native_resources_created': []}


def inventory(args):
    if args.dispatcharr_snapshot: return read_fixture(args.dispatcharr_snapshot)
    if args.remote:
        if not args.api_credentials: raise Refused('existing_private_API_login_file_required')
        credentials = private_read(args.api_credentials)
        if set(credentials) != {'username','password'}: raise Refused('API_login_schema')
        return Dispatcharr('http://127.0.0.1:9191', credentials).inventory()
    return {'accounts': [], 'channels': [], 'groups': [], 'epg_sources': [], 'epgdata': []}


def cat_for(args, p):
    if args.fixture: return catalogue(read_fixture(args.fixture))
    if not args.metadata_approval: raise Refused('fixture_or_separate_approved_metadata_path_required')
    return discover(p, MetadataHTTPS(args.metadata_approval))


def store_read(path):
    if not Path(path).exists(): return []
    with Store(path) as store:
        if store.pending() and store.pending()['state'] == 'pending':
            raise Refused('pending_operation_reconcile_first')
        return store.all()


def confirm(verb, key):
    required = verb.upper() + ' ' + key[:12]
    print('This changes private local drafts only. No Dispatcharr registration or activation.')
    if input('Type ' + required + ' to confirm: ') != required:
        raise Refused('confirmation_not_given')


def hidden(prompt):
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try: return getpass.getpass(prompt)
        except getpass.GetPassWarning: raise Refused('secure_terminal_required') from None


def show_rows(rows, redactor, label):
    items = list(rows.items())
    for offset in range(0, len(items), 50):
        for ident,row in items[offset:offset+50]: print(ident + ': ' + redactor.text(row['name']))
        if offset+50 < len(items) and input('Show next 50 '+label+'? [y/N]: ').lower() != 'y': break


def run(args):
    if getattr(args,'native',False):
        from .native_cli import run as native_run
        return native_run(args)
    if args.command in ('list','inspect'):
        rows = store_read(args.state_dir); red = Redactor()
        for b in rows: red.collect(b['provider'])
        result = {'managed_drafts': [summary(b) for b in rows],
                  'production_activation': 'BLOCKED; policy-specific review required'}
        if args.command == 'inspect' and (args.remote or args.dispatcharr_snapshot):
            inv = inventory(args); red.collect(inv)
            result['Dispatcharr_providers'] = [{k:r.get(k) for k in ['id','name','account_type','is_active','locked']} for r in inv.get('accounts',[])]
            result['Dispatcharr_ownership'] = 'All remote records are unmanaged/read-only; never adopted'
            result['channel_count_including_hidden'] = len(inv.get('channels',[]))
            result['inactive_stream_inventory_limit'] = 'Pinned API excludes inactive account streams; no deletion proof inferred'
        emit(result, red); return
    if args.command == 'reconcile':
        with Store(args.state_dir) as store:
            op = store.pending()
            if not op: raise Refused('no_pending_operation')
            emit({k:op[k] for k in ['id','kind','key','state']})
            if args.apply:
                confirm('reconcile',op['key']); emit(store.reconcile())
        return
    old = None
    if args.command == 'add':
        name = input('Provider name: ').strip()
        server = input('Xtream HTTPS base URL (no credentials/query): ').strip()
        username = input('Username: ').strip()
        password = hidden('Password (hidden): ')
        epg = hidden('Optional XMLTV HTTPS URL (hidden; Enter for provider EPG): ').strip()
        try: limit = int(input('Known maximum upstream connections (positive integer): '))
        except ValueError: raise Refused('positive_known_connection_allowance_required') from None
        p = provider(name,server,username,password,epg,limit)
        for b in store_read(args.state_dir):
            if b['provider']['key']==p['key'] or b['provider']['name']==p['name']:
                raise Refused('duplicate_managed_provider')
    else:
        with Store(args.state_dir) as store:
            old = store.get(args.key)
        p = old['provider']
    red = Redactor(p['password'],p['username']); red.collect(p)
    if args.command == 'remove':
        emit({'remove':summary(old),'effect':'archive this exact private draft; NO remote deletion',
              'affected_remote_resources':[],'dry_run':not args.apply},red)
        if args.apply:
            confirm('remove',p['key'])
            with Store(args.state_dir) as store: store.transact(p['key'],old,None,'remove')
        return
    cat = cat_for(args,p)
    inv = inventory(args); red.collect(inv)
    if args.command == 'add':
        # Presentation bounded independently of inventory size. Exact IDs remain selectable.
        show_rows(cat['groups'],red,'groups')
        print('Group rows:',len(cat['groups']),'; pages of 50. Select exact comma-separated IDs or all (limit 200).')
        groups = select(input('Groups: '),cat['groups'])
        available = {k:v for k,v in cat['channels'].items() if v['group'] in groups}
        show_rows(available,red,'channels')
        print('Channel rows:',len(available),'; pages of 50. Exact IDs or all (limit 200).')
        chosen = select(input('Channels: '),available)
    else:
        groups = old['plan']['groups']; chosen = [r['id'] for r in old['plan']['selected']]
        if not set(groups)<=set(cat['groups']) or not set(chosen)<=set(cat['channels']):
            raise Refused('selected_metadata_removed_review_required')
    proposed = plan(p,cat,groups,chosen,inv)
    if old and (old['plan']['epg_matches']!=proposed['epg_matches'] or old['plan']['selected']!=proposed['selected']):
        raise Refused('existing_selected_channel_or_EPG_mapping_changed_no_overwrite')
    bundle = {'schema':1,'owner':OWNER,'provider':p,'plan':proposed,
              'catalogue_digest':digest(cat),'snapshot_basis':'read-only API' if args.remote else 'offline snapshot' if args.dispatcharr_snapshot else 'not supplied; remote duplicates NOT checked'}
    emit({'dry_run':not args.apply,'plan':proposed,'snapshot_basis':bundle['snapshot_basis'],
          'save_effect':'private draft only; never account/channel/EPG registration'},red)
    if args.apply:
        confirm(args.command,p['key'])
        with Store(args.state_dir) as store:
            if old is None:
                if any(b['provider']['name']==p['name'] for b in store.all()):raise Refused('duplicate_managed_provider')
            store.transact(p['key'],old,bundle,args.command)
        emit({'saved':p['key'],'status':'PRIVATE DRAFT; native registration and activation BLOCKED'},red)


def parser():
    p = Parser(description=__doc__)
    p.add_argument('--state-dir',default=os.path.expanduser('~/.local/state/dispatcharr-provider'))
    sub=p.add_subparsers(dest='command',required=True,parser_class=Parser)
    for command in ['add','refresh','inspect','list','remove','reconcile']:
        s=sub.add_parser(command)
        s.add_argument('--native',action='store_true',help='Pinned native adapter; live execution blocked')
        s.add_argument('--simulate-native',action='store_true',help='Only synthetic APIs; requires --native; never production')
        if command in ['refresh','remove']:s.add_argument('key',help='Exact managed provider key; not a credential')
        if command in ['add','refresh','remove','reconcile']:s.add_argument('--apply',action='store_true',help='Confirm a local draft or explicit native simulation; never live writes')
        if command == 'reconcile':
            s.add_argument('--key',help='Native owned key, required with --native')
            s.add_argument('--fixture',help='Synthetic catalogue for native reconciliation')
        if command in ['add','refresh']:
            source=s.add_mutually_exclusive_group(required=True)
            source.add_argument('--fixture',help='Synthetic metadata JSON; no network')
            source.add_argument('--metadata-approval',help='Existing root-owned 0600 metadata-path approval; never installed by this tool')
        if command in ['add','refresh','inspect']:
            inv=s.add_mutually_exclusive_group()
            inv.add_argument('--dispatcharr-snapshot',help='Private/synthetic read-only inventory JSON')
            inv.add_argument('--remote',action='store_true',help='Read-only API inspection from approved loopback execution context')
            s.add_argument('--api-credentials',help='Existing owner-only 0600 login file; never a password argument')
    return p


def main(argv=None):
    try:
        args=parser().parse_args(argv)
        if args.simulate_native and not args.native: raise Refused('simulation_requires_native_mode')
        run(args);return 0
    except (EOFError,KeyboardInterrupt):
        print('Cancelled; no automatic retry.',file=sys.stderr);return 130
    except Refused as e:
        print('Refused: '+str(e),file=sys.stderr);return 2
    except Exception:
        print('Refused: operation_failed_details_withheld_no_retry',file=sys.stderr);return 2
