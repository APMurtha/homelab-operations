"""Opt-in integration against disposable Unix-socket Redis and exactly two fixture workers."""
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from celery_readiness import Witness, acquire, argv, capture
from dispatcharr_project import NS
from ops_collector import collect

APP = """import os
from celery import Celery
app = Celery('fixture', broker=os.environ['FIXTURE_BROKER'])
app.conf.update(broker_connection_timeout=1, broker_connection_retry_on_startup=False,
                task_default_queue='discard', worker_send_task_events=False)
"""


def proc_identity(process):
    # /proc comm can contain spaces and parentheses, so split after the last ')'.
    assert process.poll() is None
    ticks = int(Path(f'/proc/{process.pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    return process.pid, ticks


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


@unittest.skipUnless(os.environ.get('SAMWISE_CELERY_STAGE') == '1',
                     'requires isolated disposable staging dependencies')
class LiveReadiness(unittest.TestCase):
    def test_two_worker_single_broadcast_and_withdrawal(self):
        redis = Path(os.environ['SAMWISE_STAGE_REDIS']).resolve(strict=True)
        libraries = Path(os.environ['SAMWISE_STAGE_LIBRARIES']).resolve(strict=True)
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        with ExitStack() as resources:
            root = Path(resources.enter_context(tempfile.TemporaryDirectory(prefix='scstage-')))
            out = root / 'observations'
            out.mkdir(mode=0o700)
            sock = root / 'fixture.sock'
            (root/'celery_fixture.py').write_text(APP)
            env = dict(PATH='/usr/bin:/bin', HOME=str(root), PYTHONDONTWRITEBYTECODE='1',
                       PYTHONPATH=str(libraries), FIXTURE_BROKER='redis+socket://'+str(sock)+'?virtual_host=0')
            names = ('default@isolated-fixture','dvr@isolated-fixture')

            def launch(executable):
                process = subprocess.Popen(executable, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                resources.callback(stop, process)
                return process

            broker = launch([str(redis), '--port', '0', '--unixsocket', str(sock),
                             '--unixsocketperm', '700', '--save', '', '--appendonly', 'no',
                             '--daemonize', 'no', '--dir', str(root)])
            for _ in range(100):
                if sock.exists():
                    break
                self.assertIsNone(broker.poll())
                time.sleep(.05)
            self.assertTrue(sock.is_socket())
            workers = {name: launch([sys.executable, '-B', '-m', 'celery', '-A', 'celery_fixture',
                                    'worker', '--hostname='+name, '--pool=solo', '--concurrency=1',
                                    '--without-mingle', '--without-gossip', '--without-heartbeat'])
                       for name in names}

            # Wait passively for both fixture workers' real pidbox subscriptions.
            sys.path.insert(0, str(libraries))
            resources.callback(sys.path.pop, 0)
            import redis as redis_client
            client = redis_client.Redis(unix_socket_path=str(sock), socket_timeout=1)
            resources.callback(client.close)
            def subscribers():
                return sum(int(row.get('psub', 0)) > 0 for row in client.client_list())

            for _ in range(100):
                if subscribers() >= 2:
                    break
                self.assertTrue(all(p.poll() is None for p in workers.values()))
                time.sleep(.05)
            self.assertGreaterEqual(subscribers(), 2)

            started = time.time_ns()-NS

            def inspect():
                # Backend is intentionally synthetic; worker PIDs/starts and broker are real.
                row = dict(Name='/dispatcharr', Id='a'*64, Status='running', Running=True,
                           Pid=broker.pid, StartedNs=started, Health='healthy',
                           HealthEndNs=started, HealthExitCode=0)
                return Witness(boot, row, {name: proc_identity(p) for name, p in workers.items()})

            def ping(destinations):
                return capture(argv(sys.executable, 'celery_fixture', destinations), root, env)

            begin = time.monotonic()
            args = (out, os.getuid(), boot, names, inspect, ping)
            self.assertEqual(acquire(*args), 'both-ready')
            good = time.monotonic()-begin
            request = '{"observations":["celery"]}'
            self.assertEqual(collect(request,out,os.getuid()), {'celery':'both-ready'})
            stop(broker)
            begin = time.monotonic()
            self.assertEqual(acquire(*args), 'unavailable')
            fail = time.monotonic()-begin
            self.assertEqual(collect(request,out,os.getuid()), {'celery':'unavailable'})
            self.assertFalse((out/'celery').exists())
            print(f'celery_stage_ok_wall_seconds={good:.3f} broker_offline_wall_seconds={fail:.3f}')


if __name__ == '__main__':
    unittest.main()
