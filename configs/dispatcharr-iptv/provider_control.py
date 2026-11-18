"""Trusted one-shot provider cleanup/anchor preparation. No automatic grants.

Three/four-service stacks with no provider interface are valid. Partial or
unexplained status state refuses; no cleanup action adopts an anchor.
"""
import argparse
import importlib
import os
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/run/dispatcharr-provider')
PUBLIC=Path('/run/dispatcharr-provider-status')


def publisher():
    name='_dispatcharr_trusted_provider'
    if name not in sys.modules:
        pkg=types.ModuleType(name);pkg.__path__=[str(ROOT/'native-provider-hardening')];sys.modules[name]=pkg
    return importlib.import_module(name+'.publish_policy').Publisher(PRIVATE,PUBLIC)


def present(path):
    return path.exists() or path.is_symlink()


def revoke():
    if os.geteuid()!=0:raise ValueError('root_required')
    anchor=PRIVATE/'.status-anchor.json'
    if not present(PUBLIC) and not present(anchor):return  # Never initialized.
    publisher().revoke()


def assert_revoked():
    if os.geteuid()!=0:raise ValueError('root_required')
    if not present(PUBLIC) and not present(PRIVATE/'.status-anchor.json'):return
    p=publisher()
    with p.lock() as private,p.anchor(private) as public:
        if os.listdir(public):raise ValueError('provider_authorization_still_present')


def prepare():
    if os.geteuid()!=0:raise ValueError('root_required')
    if not present(PRIVATE):PRIVATE.mkdir(mode=0o700)
    p=publisher()
    if not present(PUBLIC) and not present(PRIVATE/'.status-anchor.json'):p.initialize()
    # Existing anchors are checked, never replaced, chmodded or adopted.
    with p.lock() as private,p.anchor(private):pass
    assert_revoked()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['revoke','assert-revoked','prepare'])
    a=parser.parse_args()
    try:{'revoke':revoke,'assert-revoked':assert_revoked,'prepare':prepare}[a.action]()
    except Exception:raise SystemExit('Trusted provider lifecycle refused; no automatic publication.') from None

if __name__=='__main__':main()
