"""Planned origin qualification for the fixed two-destination ping.

Redis fanout cannot attest a publisher. Only replies signed by each separately
enrolled worker over this one challenge and its current incarnation qualify.
This verifier needs no worker private keys, broker credentials, or network.
"""
import ctypes
import hashlib
import json
import re
import secrets

_DOMAIN = b'samwise/celery-readiness/origin/v1\x00'
_CRYPTO = '/usr/lib/x86_64-linux-gnu/libcrypto.so.3'
_WORD = re.compile(r'[0-9a-f]{64}')
_SIG = re.compile(r'[0-9a-f]{128}')
_NAME = re.compile(r'(?:default|dvr)@[A-Za-z0-9_.-]{1,253}')


def _require(condition):
    if not condition:
        raise ValueError('signed_origin_refused')


def _fixed(value, pattern):
    _require(type(value) is str and pattern.fullmatch(value) is not None)
    return value


def _names(names):
    _require(type(names) is list and len(names) == 2)
    return tuple(_fixed(n, _NAME) for n in names)


def _nat(value):
    _require(type(value) is int and 0 < value < 2**63)
    return value


def _word(value):
    return _fixed(value, _WORD)


def challenge():
    return secrets.token_hex(32)


def statement(nonce, scope, worker, incarnation):
    """Bind a fresh random challenge, exact broker scope and worker incarnation.

    Incarnation is a SHA256 of the immutable enrolled site/boot/backend ID and
    the host+guest PID/start tuples. It is not a secret or itself an authority.
    """
    value = [_word(nonce), _word(scope), _fixed(worker, _NAME), _word(incarnation)]
    return _DOMAIN + json.dumps(value,separators=(',',':'),ensure_ascii=True).encode('ascii')


def incarnation(*, site, boot, backend, host_pid, guest_pid, ticks):
    _require(type(site) is str and re.fullmatch(r'[a-z0-9-]{1,63}',site))
    _require(type(boot) is str and re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',boot))
    value = [site, boot, _word(backend), _nat(host_pid), _nat(guest_pid), _nat(ticks)]
    return hashlib.sha256(json.dumps(value,separators=(',',':')).encode('ascii')).hexdigest()


def verify_ed25519(public_key, message, signature):
    """Use the fixed installed OpenSSL 3 library, no subprocess or raw logs."""
    _require(type(public_key) is bytes and len(public_key)==32 and
             type(message) is bytes and 0<len(message)<=512 and
             type(signature) is bytes and len(signature)==64)
    lib = ctypes.CDLL(_CRYPTO)
    ptr, string, size, integer = ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int
    def function(name, result, *args):
        result_fn = getattr(lib,name)
        result_fn.restype,result_fn.argtypes=result,list(args)
        return result_fn
    pkey_new = function('EVP_PKEY_new_raw_public_key_ex',ptr,ptr,string,string,string,size)
    pkey_free = function('EVP_PKEY_free',None,ptr)
    context_new = function('EVP_MD_CTX_new',ptr)
    context_free = function('EVP_MD_CTX_free',None,ptr)
    init = function('EVP_DigestVerifyInit',integer,ptr,ptr,ptr,ptr,ptr)
    verify = function('EVP_DigestVerify',integer,ptr,string,size,string,size)
    key=pkey_new(None,b'ED25519',None,public_key,len(public_key))
    _require(bool(key))
    try:
        ctx=context_new()
        _require(bool(ctx))
        try:
            _require(init(ctx,None,None,None,key)==1)
            return verify(ctx,signature,len(signature),message,len(message))==1
        finally:
            context_free(ctx)
    finally:
        pkey_free(key)


def qualify(raw, names, keys, incarnations, nonce, scope, verify=verify_ed25519):
    """Normalize only authenticated frames. Timeout/ambiguity is unavailable."""
    ordered = _names(names)
    _require(tuple(n.split('@',1)[0] for n in ordered)==('default','dvr'))
    _require(type(keys) is dict and type(incarnations) is dict and
             set(keys)==set(incarnations)==set(ordered))
    _require(len({_word(keys[n]) for n in ordered})==len(ordered) and
             len({_word(incarnations[n]) for n in ordered})==len(ordered))
    _require(type(raw) is list and 0<len(raw)<=2)
    output={}
    for frame in raw:
        _require(type(frame) is dict and len(frame)==1)
        worker,pong=next(iter(frame.items()))
        _require(worker in ordered and worker not in output and
                 type(pong) is dict and set(pong)=={'ok','origin'} and pong['ok']=='pong')
        origin=pong['origin']
        _require(type(origin) is dict and set(origin)=={'version','incarnation','signature'} and
                 origin['version']==1 and type(origin['version']) is int and
                 origin['incarnation']==incarnations[worker])
        signature=bytes.fromhex(_fixed(origin['signature'],_SIG))
        message=statement(nonce,scope,worker,incarnations[worker])
        _require(verify(bytes.fromhex(keys[worker]),message,signature) is True)
        output[worker]={'ok':'pong'}
    return output
