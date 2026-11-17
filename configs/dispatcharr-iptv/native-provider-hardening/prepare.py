#!/usr/bin/env python3
"""Produce an exact-pinned source overlay and unified patch; never builds images.

Only input is a local source tree at the accepted commit. No network, subprocess,
production path, Docker or service action exists here. Output must be a new dir.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

BASE=Path(__file__).resolve().parent
PINS=json.loads((BASE/'source-pins.json').read_text())


def edit_function(text,name,prefix='',wrap=None,signature=None,replacement=None):
    tree=ast.parse(text)
    nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
    if len(nodes)!=1: raise ValueError('function_identity_conflict: '+name)
    n=nodes[0]; lines=text.splitlines(keepends=True); start=n.body[0].lineno-1;end=n.end_lineno
    indent=' '*(n.col_offset+4)
    if replacement is not None: body=''.join(indent+l+'\n' for l in replacement.splitlines())
    else:
        body=''.join(indent+l+'\n' for l in prefix.splitlines())
        old=''.join(lines[start:end])
        if wrap: body+=indent+wrap+'\n'+''.join('    '+l if l.strip() else l for l in lines[start:end])
        else: body+=old
    lines[start:end]=[body]
    if signature:
        # Function signatures affected here are deliberately single-line and pinned.
        lines[n.lineno-1]=signature+'\n'
    return ''.join(lines)



def task_options(text,name):
    fn=next(n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name==name)
    decorator=next(d for d in fn.decorator_list if isinstance(d,ast.Call) and isinstance(d.func,ast.Name) and d.func.id=='shared_task')
    decorator.keywords += [ast.keyword(arg='acks_late',value=ast.Constant(False)),ast.keyword(arg='reject_on_worker_lost',value=ast.Constant(False)),ast.keyword(arg='autoretry_for',value=ast.Tuple(elts=[],ctx=ast.Load()))]
    lines=text.splitlines(True);start=sum(map(len,lines[:decorator.lineno-1]))+decorator.col_offset;end=sum(map(len,lines[:decorator.end_lineno-1]))+decorator.end_col_offset
    return text[:start]+ast.unparse(decorator)+text[end:]


def change(path,text):
    imports='from core.provider_security import (Denied, SafeLogger, progress, job, remote, xmltv_download, xc_get, contract, safe_errors, media_url)\n'
    if path.endswith(('tasks.py','signals.py','api_views.py','xtream_codes.py')): text=imports+text
    if path=='core/xtream_codes.py':
        text=text.replace('logger = logging.getLogger(__name__)','logger = SafeLogger(__name__)')
        start=text.index('        # Create persistent session');end=text.index('        self.server_info = None',start)
        text=text[:start]+"        from core.provider_security import NoSession\n        self.session = NoSession()\n\n"+text[end:]
        text=edit_function(text,'_make_request',replacement='return xc_get(self.server_url, endpoint, params or {})')
        for name,kind,extension in [('get_stream_url','live',"'ts'"),('get_episode_stream_url','series','container_extension'),('get_vod_stream_url','movie','container_extension')]:
            text=edit_function(text,name,replacement=f"return media_url(self.server_url, self.username, self.password, stream_id, {kind!r}, {extension})")
        # Exception details from authentication/response validation must never
        # escape into an API response or another task's diagnostics.
        methods=[n.name for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.col_offset==4 and n.name not in ('_make_request','__del__','close','__enter__','__exit__')]
        for name in methods:
            text=edit_function(text,name,wrap='with safe_errors():')
    elif path=='apps/m3u/api_views.py':
        # Only the ViewSet create contains this exact XC branch.
        text=text.replace('if account_type == M3UAccount.Types.XC:\n            refresh_m3u_groups(account_id)',
            'if account_type == M3UAccount.Types.XC and request.data.get("metadata_discovery") is True:\n            with job("discover", M3UAccount.objects.get(id=account_id), True):\n                refresh_m3u_groups(account_id)')
        text=text.replace('refresh_single_m3u_account.delay(account_id)','refresh_single_m3u_account.delay(account_id, operator_requested=True)')
    elif path=='apps/m3u/tasks.py':
        text=text.replace('logger = logging.getLogger(__name__)','logger = SafeLogger(__name__)')
        text=task_options(text,'refresh_single_m3u_account')
        text=edit_function(text,'check_field_lengths',replacement='return None')
        text=text.replace('refresh_account_profiles.delay(account.id)', 'None  # automatic credential-bearing profile refresh disabled')
        text=text.replace('tvg_logo = stream.get("stream_icon", "")', 'tvg_logo = ""')
        text=edit_function(text,'refresh_single_m3u_account',wrap='with job("refresh", M3UAccount.objects.get(id=account_id), operator_requested):',
            signature='def refresh_single_m3u_account(account_id, operator_requested=False):')
        for name in ('refresh_account_profiles','refresh_account_info'):
            text=edit_function(text,name,replacement='return "automatic_native_profile_refresh_disabled"')
        # No alternative requests-based remote playlist path may bypass the new
        # metadata boundary; local/custom DW streams do not use this downloader.
        text=text.replace('response = requests.get(', 'response = denied_remote_playlist(')
        text=text.replace('\"tvg-logo\": stream.get(\"stream_icon\", \"\")', '\"tvg-logo\": \"\"')
        text=text.replace('\"url\": f\"{stream_url_prefix}{stream_id}.ts\"', '\"url\": xc_client.get_stream_url(stream_id)')
        text=text.replace('''            stream_url_prefix = (
                f"{xc_client.server_url.rstrip('/')}/live/"
                f"{xc_client.username}/{xc_client.password}/"
            )''', '')
        text+='\n# Provider-derived diagnostic bodies are never forwarded to logs/websockets.\nsend_m3u_update = progress\nlog_system_event = progress\n'
        text='from core.provider_security import denied_remote_playlist\n'+text
    elif path=='apps/m3u/signals.py':
        text=text.replace('should_be_enabled = instance.is_active','should_be_enabled = instance.is_active and instance.account_type != "XC"')
    elif path=='apps/epg/api_views.py':
        text=text.replace('refresh_epg_data.delay(epg_id, force=force)', 'refresh_epg_data.delay(epg_id, force=force, operator_requested=True)')
    elif path=='apps/epg/signals.py':
        text=text.replace("if created and instance.is_active and instance.source_type != 'dummy':", "if created and instance.is_active and instance.source_type != 'dummy' and not remote(instance):")
        text=text.replace('should_be_enabled = instance.is_active','should_be_enabled = instance.is_active and not remote(instance)')
    elif path=='apps/epg/tasks.py':
        text=task_options(text,'refresh_epg_data')
        text=text.replace('logger = logging.getLogger(__name__)','logger = SafeLogger(__name__)')
        # Global refresh deliberately remains available to unrelated local/dummy
        # sources. Remote XMLTV jobs require a scoped explicit API request.
        text=text.replace("active_sources = EPGSource.objects.filter(is_active=True).exclude(source_type='dummy')",
                          "active_sources = EPGSource.objects.filter(is_active=True).exclude(source_type='dummy').exclude(source_type='xmltv', url__gt='')")
        text=edit_function(text,'refresh_epg_data',wrap='with job("epg", _get_epg_source(source_id), operator_requested):',
            signature='def refresh_epg_data(source_id, force=False, _file_defer_retry=0, operator_requested=False):')
        # A source-less global task is rejected before querying. The adapter must
        # always specify one owned source ID.
        text=edit_function(text,'refresh_epg_data',prefix='if type(source_id) is not int or source_id <= 0: raise Denied()')
        text=edit_function(text,'fetch_xmltv',prefix='if source.url: return xmltv_download(source)')
        text=text.replace('        evaluate_series_rules.delay()', '        if not remote(source): evaluate_series_rules.delay()')
        text=text.replace('        maybe_auto_apply_epg_logos(source)', '        if not remote(source): maybe_auto_apply_epg_logos(source)')
        text=edit_function(text,'parse_programs_for_tvg_id',prefix='candidate = EPGData.objects.select_related("epg_source").filter(id=epg_id).first()\nif candidate and remote(candidate.epg_source): return "automatic_remote_programme_parse_disabled"')
        text=edit_function(text,'_parse_programme_element',replacement='parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, recover=False, huge_tree=False)\nreturn etree.fromstring(element_bytes, parser)')
        # Replace every lxml streaming parser call, including multiline ones.
        for node in sorted([n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='etree' and n.func.attr=='iterparse'],key=lambda n:(n.lineno,n.col_offset),reverse=True):
            node.keywords=[k for k in node.keywords if k.arg not in ('resolve_entities','load_dtd','no_network','recover','huge_tree')]
            node.keywords += [ast.keyword(arg=k,value=ast.Constant(value=v)) for k,v in [('resolve_entities',False),('load_dtd',False),('no_network',True),('recover',False),('huge_tree',False)]]
            lines=text.splitlines(keepends=True);start=sum(map(len,lines[:node.lineno-1]))+node.col_offset;end=sum(map(len,lines[:node.end_lineno-1]))+node.end_col_offset
            text=text[:start]+ast.unparse(node)+text[end:]
        text+='\nsend_epg_update = progress\nlog_system_event = progress\n'
    elif path=='core/api_urls.py':
        text+='\nfrom .provider_security_view import provider_security\nurlpatterns += [path("provider-security/", provider_security, name="provider_security")]\n'
    # Stored error text must not preserve a raw exception/URL, either.
    if path in ('apps/m3u/tasks.py','apps/epg/tasks.py'):
        func='_set_m3u_account_status' if '/m3u/' in path else '_set_epg_source_status'
        text=edit_function(text,func,prefix='last_message = "native_metadata_status" if last_message is not None else None\nws_error = "native_metadata_error" if ws_error is not None else None')
        nodes=[n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='last_message' for t in n.targets)]
        lines=text.splitlines(keepends=True)
        for n in sorted(nodes,key=lambda n:n.lineno,reverse=True):
            line=' ' * n.col_offset+ast.unparse(n.targets[0])+' = "native_metadata_status"\n'
            lines[n.lineno-1:n.end_lineno]=[line]
        text=''.join(lines)
    ast.parse(text)
    return text


def prepare(source,output):
    if output.exists(): raise ValueError('new_output_directory_required')
    originals={}
    for name,sha in PINS.items():
        data=(source/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=sha: raise ValueError('pinned_source_mismatch: '+name)
        originals[name]=data.decode()
    # All pins verified before writing any output.
    output.mkdir(parents=True)
    hashes={};patch=[]
    for name,old in originals.items():
        new=change(name,old);target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(new)
        hashes[name]=hashlib.sha256(new.encode()).hexdigest()
        patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    for path in sorted((BASE/'runtime').glob('*.py')):
        target=output/'core'/path.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(path,target)
        hashes['core/'+path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        patch.extend(difflib.unified_diff([],path.read_text().splitlines(True),fromfile='/dev/null',tofile='b/core/'+path.name))
    # Manifest is image data, not an authorization/policy file.
    manifest=json.dumps(hashes,indent=2,sort_keys=True)+'\n'
    (output/'core/provider_contract_hashes.json').write_text(manifest)
    patch.extend(difflib.unified_diff([],manifest.splitlines(True),fromfile='/dev/null',tofile='b/core/provider_contract_hashes.json'))
    (output/'server.patch').write_text(''.join(patch))
    (output/'output-hashes.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')
    return hashes


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.source,a.output)
