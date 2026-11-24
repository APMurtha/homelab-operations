"""Offline construction tests; never install a seccomp or Landlock filter."""
import ctypes
import socket
import unittest
from pathlib import Path

import celery_broker_guard as g


class GuardShape(unittest.TestCase):
    def denied(self, name, args=()):
        def comparison(item):
            val = args[item.arg]
            return {g.NE: val != item.a, g.EQ: val == item.a,
                    g.GT: val > item.a,
                    g.MASKED_EQ: val & item.a == item.b}[item.op]
        return any(test == name and all(comparison(c) for c in compares)
                   for test, compares in g.reject_rules())

    def test_native_struct_and_fixed_target(self):
        self.assertEqual((ctypes.sizeof(g.Ruleset), ctypes.sizeof(g.PathRule),
                          ctypes.sizeof(g.NetRule)), (24, 12, 16))
        self.assertEqual(g.PORT, 6379)
        self.assertEqual(g.MIN_ABI, 6)
        self.assertEqual(g.RUNTIME, Path('/opt/samwise-celery-shadow/pidbox-runtime.zip'))

    def test_only_unconnected_ipv4_tcp_sockets_can_be_created(self):
        for family in (socket.AF_UNIX, socket.AF_INET6, socket.AF_NETLINK):
            self.assertTrue(self.denied('socket', (family, socket.SOCK_STREAM, 0)))
        for kind in range(16):
            for protocol in range(257):
                self.assertEqual(self.denied('socket', (socket.AF_INET, kind, protocol)),
                                 kind != socket.SOCK_STREAM or protocol not in (0, 6))
        self.assertFalse(self.denied('socket', (socket.AF_INET,
                         socket.SOCK_STREAM | socket.SOCK_CLOEXEC, socket.IPPROTO_TCP)))

    def test_denies_process_socket_escape_paths(self):
        for name in ('bind', 'listen', 'accept', 'accept4', 'socketpair', 'clone3',
                     'execveat', 'setns', 'bpf', 'io_uring_setup', 'pidfd_getfd'):
            self.assertTrue(self.denied(name))
        self.assertFalse(self.denied('sendto', (42, 0, 0, 0, 0)))
        self.assertTrue(self.denied('sendto', (42, 0, 0, 0, 0x1234)))

    def test_alternate_archive_refuses_before_policy_activation(self):
        with self.assertRaises(ValueError):
            g.apply('/tmp/controlled-but-not-enrolled.zip')


if __name__ == '__main__':
    unittest.main()
