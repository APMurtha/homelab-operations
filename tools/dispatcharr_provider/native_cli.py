"""Explicit native mode. --simulate-native runs synthetic APIs, never HTTP."""
from pathlib import Path
from .core import Refused, Redactor, Store, private_read, catalogue, plan
from .native import API, Adapter, Ledger, LiveBlocked
from .synthetic import Synthetic


def run(args):
    # Import lazily to preserve the existing draft CLI without dependency cycles.
    from .cli import emit, read_fixture, hidden, show_rows, select, provider
    root = Path(args.state_dir) / 'native'
    if args.command in ('inspect','list'):
        if getattr(args,'remote',False) or getattr(args,'api_credentials',None) or getattr(args,'dispatcharr_snapshot',None):
            raise Refused('native_inventory_is_local_ledger_only_use_legacy_read_only_inspect')
        result = []
        if root.exists():
            with Store(root) as store:
                paths = sorted(root.glob('native-*.json'))
                if len(paths) > 1000: raise Refused('native_ledger_inventory_limit')
                for path in paths:
                    ledger = Ledger(store,path.stem.removeprefix('native-'))
                    result.append(Adapter(API(LiveBlocked()),ledger).summary())
        emit({'native_registrations':result,'live_execution':'BLOCKED','all_entries_are_simulations':True})
        return
    if args.command == 'remove':
        raise Refused('native_removal_disabled_cascade_and_shared_resource_safety_unproven')
    if not args.simulate_native:
        # Fail before asking for credentials, authentication, creating state or
        # contacting any source. Metadata approval cannot authorize server I/O.
        raise Refused('native_live_execution_blocked_server_network_and_logging_review_required')
    if not getattr(args,'fixture',None): raise Refused('native_simulation_requires_synthetic_fixture')
    if args.command == 'reconcile' and not getattr(args,'key',None): raise Refused('native_reconcile_requires_key')
    cat = catalogue(read_fixture(args.fixture))
    snapshot = read_fixture(args.dispatcharr_snapshot) if getattr(args,'dispatcharr_snapshot',None) else {}
    if getattr(args,'remote',False) or getattr(args,'metadata_approval',None) or getattr(args,'api_credentials',None):
        raise Refused('native_simulation_no_network_inputs')
    if args.command == 'add':
        name = input('Provider name: ').strip()
        server = input('Xtream HTTPS base URL: ').strip()
        username = input('Username: ').strip()
        password = hidden('Password (hidden): ')
        epg = hidden('Optional XMLTV HTTPS URL (hidden; Enter for provider EPG): ').strip()
        try: limit = int(input('Known maximum upstream connections: '))
        except ValueError: raise Refused('positive_known_connection_allowance_required') from None
        p = provider(name,server,username,password,epg,limit)
        red = Redactor(); red.collect(p)
        show_rows(cat['groups'],red,'groups'); groups = select(input('Groups: '),cat['groups'])
        available = {k:v for k,v in cat['channels'].items() if v['group'] in groups}
        show_rows(available,red,'channels'); selected = select(input('Channels: '),available)
        proposed = plan(p,cat,groups,selected,snapshot)
        emit({'simulation':True,'dry_run':not args.apply,'native_plan':{
            'provider_key':p['key'],'provider_name':p['name'],'selected':proposed['selected'],
            'EPG_strategy':'exact stable identifier within newly owned source; missing remains unmapped',
            'existing_resources_affected':[], 'native_state_after_import':'hidden channels; inactive account/source',
            'side_effects':['synchronous XC authentication/categories; queued account profile metadata',
                            'all category stream metadata; temporarily enabled periodic tasks; EPG import'],
            'streaming_activation':'BLOCKED; no relay or Jellyfin exports',
            'network_security':'native live transport disabled; fixture simulation only'}},red)
        if not args.apply: return
    else:
        with Store(root) as store:
            ledger = Ledger(store,args.key)
            if not ledger.value: raise Refused('native_owned_provider_missing')
            p = ledger.value['provider']
        red = Redactor(); red.collect(p)
        emit({'simulation':True,'key':p['key'],'provider_name':p['name'],'operation':args.command,
              'selected':ledger.value['selected'],'owned_resources':Adapter(API(LiveBlocked()),ledger).summary(),
              'EPG_strategy':'preserve exact source-scoped native IDs; refuse changes',
              'effect':'metadata refresh only; no channel additions, remapping or media activation',
              'dry_run':not args.apply},red)
        if not args.apply: return
    required = 'SIMULATE ' + args.command.upper() + ' ' + p['key'][:12]
    if input('Offline synthetic API writes only. Type '+required+': ') != required:
        raise Refused('native_confirmation_not_given')
    with Store(root) as store:
        ledger = Ledger(store,p['key'])
        transport = Synthetic(cat,store.root/('synthetic-'+p['key']+'.json'),snapshot)
        adapter = Adapter(API(transport),ledger,pause=lambda _:None,progress=print)
        if args.command == 'add':
            for path in store.root.glob('native-*.json'):
                existing = Ledger(store,path.stem.removeprefix('native-')).value
                if existing and (existing['key'] == p['key'] or existing['provider']['name'] == p['name']):
                    raise Refused('native_duplicate_managed_provider')
            result = adapter.register(p,proposed['selected'],1)
        elif args.command == 'refresh': result = adapter.refresh()
        elif args.command == 'reconcile': result = ledger.reconcile(adapter.api)
        else: raise Refused('native_command_unsupported')
        emit(result,red)
