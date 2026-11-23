import copy
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from engine_health.acquire import capture, response
from dispatcharr_project import CONTAINERS
from ops_collector import collect
from engine_health.release import load, release

S = 1800000000_000000000
T = '2027-01-15T08:00:00.000000000Z'


def obj(name):
    return dict(Name='/'+CONTAINERS[name], Id=('%x'%(list(CONTAINERS).index(name)+1))*64, Config=dict(Env=['private-canary']),
                State=dict(Status='running', Running=True, Dead=False, Restarting=False,
                           Paused=False, Pid=123+list(CONTAINERS).index(name), StartedAt='2027-01-14T00:00:00Z',
                           Health=dict(Status='healthy', Log=[dict(Start=T, End=T,
                                     ExitCode=0, Output='private-canary')])))


def packet(obj, chunk=False):
    raw=json.dumps(obj).encode()
    head=b'HTTP/1.1 200 OK\r\n'
    if chunk:
        return head+b'Transfer-Encoding: chunked\r\n\r\n'+b'%x\r\n'%len(raw)+raw+b'\r\n0\r\n\r\n'
    return head+b'Content-Length: %d\r\n\r\n'%len(raw)+raw


class Evidence(unittest.TestCase):
    def setUp(self):
        self.a=[obj(n) for n in CONTAINERS]
        self.b=copy.deepcopy(self.a)

    def batch(self, lag=0):
        return capture(io.BytesIO(b''.join(packet(x) for x in self.a)+
                                  b''.join(packet(x,True) for x in self.b)),
                       S+lag,lambda:S+lag+100)

    def test_complete_and_private(self):
        d=self.batch()
        self.assertEqual(set(d['records']),set(CONTAINERS))
        self.assertNotIn('private-canary',str(d))
        self.assertEqual(d['records']['backend'][1]['HealthEndNs'],S)

    def test_id_pid_restart_name_time_and_state(self):
        for key, value in [('Id','b'*64),('Name','/wrong'),('Pid',224),
                           ('StartedAt','2027-01-14T01:00:00Z'),('Paused',True),
                           ('Restarting',True),('Dead',True),('Running',False)]:
            with self.subTest(key=key):
                self.b=copy.deepcopy(self.a)
                dst=self.b[0] if key in ('Id','Name') else self.b[0]['State']
                dst[key]=value
                self.assertEqual(set(self.batch()['records']),set(CONTAINERS)-{'backend'})

    def test_cross_topic_identity_collision(self):
        for key in ('Id','Pid'):
            self.b=copy.deepcopy(self.a)
            rows=self.b if key=='Id' else [x['State'] for x in self.b]
            rows[1][key]=rows[0][key]
            self.assertEqual(set(self.batch()['records']),{'vpn-container','jellyfin'})

    def test_complete_negative_states(self):
        for obj in (self.a[0],self.b[0]):
            obj['State']['Health']['Status']='unhealthy'
            obj['State']['Health']['Log'][0]['ExitCode']=1
        for obj in (self.a[1],self.b[1]):
            obj['State'].update(Status='exited',Running=False,Pid=0)
        d=self.batch()
        with tempfile.TemporaryDirectory() as t:
            fd=os.open(t,os.O_DIRECTORY);self.addCleanup(os.close,fd)
            release(fd,(d['began'],d['ended'],d['records']))
            with patch('time.time_ns',return_value=S+101):
                self.assertEqual(collect('{"observations":["backend","gateway"]}',Path(t),os.getuid()),
                                 {'backend':'unhealthy','gateway':'stopped'})

    def test_contradictory_or_missing_health(self):
        for key,value in [('ExitCode',1),('ExitCode',False),('End','2028-01-01T00:00:00Z'),
                          ('Start','2027-01-15T09:00:00Z')]:
            self.b=copy.deepcopy(self.a)
            self.b[0]['State']['Health']['Log'][0][key]=value
            self.assertNotIn('backend',self.batch()['records'])
        self.a[0]['State']['Health']['Log']=[]
        self.assertNotIn('backend',self.batch()['records'])

    def test_truncated_conflicting_and_oversize(self):
        for body in [b'HTTP/1.1 200 OK\r\nContent-Length: 524289\r\n\r\n',
                     b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{',
                     b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nTransfer-Encoding: chunked\r\n\r\n',
                     b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nx']:
            with self.assertRaises(ValueError):
                response(io.BytesIO(body))

    def test_stale_cannot_be_renewed_and_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); fd=os.open(t,os.O_DIRECTORY)
            self.addCleanup(os.close,fd)
            (p/'relay').write_text('untouched')
            d=self.batch(70_000000000)
            release(fd,(d['began'],d['ended'],d['records']))
            with patch('time.time_ns',return_value=d['ended']):
                self.assertEqual(collect('{"observations":["backend"]}',p,os.getuid()),{'backend':'stale'})
            self.assertEqual((p/'backend').stat().st_mtime_ns,S)
            release(fd,(0,0,{}))
            self.assertEqual(list(p.iterdir()),[p/'relay'])

    def test_cache_ownership_mode_and_replay(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'batch';fd=os.open(t,os.O_DIRECTORY);self.addCleanup(os.close,fd)
            d=self.batch();p.write_text(json.dumps(d));p.chmod(0o600)
            os.utime(p,ns=(S,S))
            self.assertEqual(set(load(fd,os.getuid(),S+100)[2]),set(CONTAINERS))
            for uid,now in [(os.getuid()+1,S+100),(os.getuid(),S+6_000000000)]:
                with self.assertRaises(ValueError): load(fd,uid,now)
            p.chmod(0o666)
            with self.assertRaises(ValueError): load(fd,os.getuid(),S+100)


if __name__=='__main__':
    unittest.main()
