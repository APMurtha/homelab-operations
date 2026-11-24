import json
from types import SimpleNamespace as Simple
from unittest.mock import Mock
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import celery_site_pidbox as site


class PidboxRules(unittest.TestCase):
    def test_expect_exact_worker_roles_and_raw_reply_uniqueness(self):
        names = ['default@fixture','dvr@fixture']
        one = {names[0]:{'ok':'pong'}}
        two = {names[1]:{'ok':'pong'}}
        self.assertEqual(site.replies([one,two],names,lambda:None),one|two)
        for frames in ([one], [two], [one,one], [one,two,one], [{**one, **two}], [],
                       [{'default@wrong':{'ok':'pong'}}], [{names[0]:{'ok':'pong','noise':1}}]):
            with self.subTest(frames=frames),self.assertRaises(ValueError):
                site.replies(frames,names,lambda:None)

    def test_one_targeted_ping_keeps_raw_third_reply_visible(self):
        names=['default@fixture','dvr@fixture']
        box=Simple(exchange=Simple(name='celery.pidbox'),
                   reply_exchange=Simple(name='reply.celery.pidbox'),serializer='json')
        channel=Simple(keyprefix_fanout='/0.',fanout_patterns=True,global_keyprefix='',
                       _get_publish_topic=lambda exchange,key:'/0.'+exchange)
        conn=Mock(hostname=site.HOST,port=site.PORT,virtual_host='/0',alt=[],ssl=False,
                  userid=None,password=None,default_channel=channel)
        conn.__enter__=Mock(return_value=conn)
        conn.__exit__=Mock(return_value=False)
        app=Mock(conf={},control=Simple(mailbox=box,broadcast=Mock()),connect=None)
        app.connection_for_write.return_value=conn
        first={names[0]:{'ok':'pong'}}
        second={names[1]:{'ok':'pong'}}
        for raw,accepted in (([first,second],True),([first,second,first],False),
                             ([first,second,{'default@extra':{'ok':'pong'}}],False)):
            app.control.broadcast.reset_mock()
            app.control.broadcast.return_value=raw
            with self.subTest(raw=raw):
                if accepted:
                    self.assertEqual(site.capture(lambda *_a,**_k:app,names,lambda:None),first|second)
                else:
                    with self.assertRaises(ValueError):
                        site.capture(lambda *_a,**_k:app,names,lambda:None)
                app.control.broadcast.assert_called_once_with('ping',arguments={},destination=names,
                           connection=conn,channel=channel,reply=True,timeout=8,limit=3)

    def test_decoy_port_foreign_address_and_socket_families_refused(self):
        site.network_event('socket.connect',(None,('127.0.0.1',6379)))
        for name,args in [('socket.connect',(None,('127.0.0.1',6380))),
                          ('socket.connect',(None,('192.0.2.1',6379))),
                          ('socket.connect',(None,'/run/redis.sock')),
                          ('socket.getaddrinfo',('fake',6379)),
                          ('socket.__new__',(None,socket.AF_INET6,socket.SOCK_STREAM)),
                          ('socket.__new__',(None,socket.AF_INET,socket.SOCK_DGRAM)),
                          ('subprocess.Popen',())]:
            with self.subTest(name=name,args=args),self.assertRaises(ValueError):
                site.network_event(name,args)

    def test_operational_entry_cannot_dial_after_proc_or_enrollment_rebinding(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = Path(temp)
            boot = proc/'sys/kernel/random/boot_id'
            boot.parent.mkdir(parents=True)
            boot.write_text('11111111-2222-3333-4444-555555555555\n')
            ns = proc/'self/ns/net'
            ns.parent.mkdir(parents=True)
            ns.touch()
            cgroup = proc/'self/cgroup'
            cgroup.write_text('0::/system.slice/samwise-celery-shadow-once.service\n')
            enrolled = {'boot':boot.read_text().strip(), 'net_inode':ns.stat().st_ino}
            args=['--deadline-ns=12000000000','--enrollment-sha='+'b'*64]
            args_ok = site.operational_invocation(enrolled,args,'b'*64,proc,10**9)
            self.assertEqual(args_ok,12*10**9)
            for p,a,h,n in ((enrolled | {'net_inode':ns.stat().st_ino+1},args,'b'*64,10**9),
                            (enrolled | {'boot':'wrong'},args,'b'*64,10**9),
                            (enrolled,args,'c'*64,10**9),
                            (enrolled,args,'b'*64,12*10**9),
                            (enrolled,args+['--extra'],'b'*64,10**9)):
                with self.assertRaises(ValueError):
                    site.operational_invocation(p,a,h,proc,n)
            cgroup.write_text('0::/system.slice/another.service\n')
            with self.assertRaises(ValueError):
                site.operational_invocation(enrolled,args,'b'*64,proc,10**9)

    def test_db_control_scope_and_namespace_proof_are_fixed(self):
        scope = site.digest(site.canonical(site.SCOPE))
        p=dict(version=site.OPERATIONAL,boot='1ee950ea-57f1-4c0e-b127-dbf0b23dc841',
            net_inode=42,scope_sha256=scope,names=['default@fixture','dvr@fixture'],
            runtime_sha256='a'*64,broker_guard_sha256='b'*64,boundary_sha256='c'*64)
        self.assertEqual(site.enrollment(site.canonical(p)),p)
        for change in (dict(version='unknown'),dict(runtime_sha256='bad'),
                       dict(scope_sha256=site.digest(site.canonical(site.SCOPE|{'database':1}))),
                       dict(scope_sha256=site.digest(site.canonical(site.SCOPE|{'fanout_prefix':''}))),
                       dict(scope_sha256=site.digest(site.canonical(site.SCOPE|{'reply_exchange':'foreign'})))):
            with self.subTest(change=change),self.assertRaises(ValueError):
                site.enrollment(site.canonical(p|change))


if __name__=='__main__':
    unittest.main()
