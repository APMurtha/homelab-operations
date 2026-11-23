"""Synthetic structured reply decisions and sanitized receipt compatibility."""
import json
import sys
import unittest
from unittest.mock import patch

from test_diagnostics import B, BackendFixture, HERE, SECRET, capture
from test_structured_celery import GOOD, run_response


class ReplyRejectionTests(unittest.TestCase):
    def test_rejection_table_and_legacy_api(self):
        cases = [
            ('{}', '', 1, 'capture_incomplete'),
            (b'{}', '', True, 'non_text'),
            ('{}', None, True, 'non_text'),
            ('{}', SECRET, True, 'stderr_present'),
            ('é' * (B.OUTPUT_LIMIT // 2 + 1), '', True, 'output_oversized'),
            ('\ud800', '', True, 'invalid_utf8'),
            ('{}{}', '', True, 'malformed_json'),
            ('[' * 2000 + '!', '', True, 'malformed_json'),
            ('{"default@x":{"ok":"pong","ok":"pong"}}', '', True, 'duplicate_key'),
            ('{"default@x":{},"default@x":{}}', '', True, 'duplicate_key'),
            ('{"default@x":-Infinity}', '', True, 'nonfinite_constant'),
            ('[]', '', True, 'invalid_top_level'),
            ('{"a":1,"b":2,"c":3}', '', True, 'invalid_top_level'),
            (json.dumps({'dvr@' + 'a' * 254: {}}), '', True, 'invalid_identity'),
            (json.dumps({'default@é': {}}), '', True, 'invalid_identity'),
            ('{"dvr@a":{"ok":"pong"},"dvr@b":{"ok":"pong"}}', '', True, 'duplicate_role'),
            (json.dumps({'default@x': {'ok': 'pong'}, 'dvr@y': SECRET}), '', True, 'invalid_payload'),
        ]
        self.assertEqual({row[-1] for row in cases}, {r.value for r in B.ReplyRejection})
        for stdout, stderr, complete, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(B.structured_replies_with_reason(stdout, stderr, complete), ([], reason))
                self.assertEqual(B.structured_replies(stdout, stderr, complete), ([], False))

    def test_valid_boundaries_and_role_order(self):
        exact = json.dumps(GOOD).ljust(B.OUTPUT_LIMIT)
        cases = [(exact, ['default', 'dvr']), ('{}', []),
                 (json.dumps({'dvr@' + 'A' * 253: {'ok': 'pong'}}), ['dvr']),
                 (r' {"dvr@_.-":{"ok":"p\u006fng"},"default@0":{"ok":"pong"}} ', ['dvr', 'default'])]
        for raw, roles in cases:
            self.assertEqual(B.structured_replies_with_reason(raw, ''), (roles, None))
            self.assertEqual(B.structured_replies(raw, ''), (roles, True))

    def test_receipt_round_trip_and_old_record(self):
        rows, error, text = run_response({'default@private-host': {'error': SECRET}})
        self.assertIsNotNone(error)
        self.assertNotIn('private-host', text)
        receipt = capture(text, 1)
        self.assertEqual(receipt['reason'], 'backend_stage_failed')
        self.assertEqual(receipt['records'], rows)
        old = dict(rows[-1])
        self.assertEqual(old.pop('reply_rejection'), 'invalid_payload')
        self.assertEqual(B.decode_record(json.dumps(old)), old)
        for bad in [SECRET, 1, None, {}, []]:
            with self.assertRaises(B.InvalidDiagnostics):
                B.decode_record(json.dumps(dict(old, reply_rejection=bad)))

    def test_valid_results_never_have_rejections(self):
        for mapping, code in [(GOOD, 0), (GOOD, 69), ({}, 0),
                              ({'default@x': {'ok': 'pong'}}, 0), ({'dvr@x': {'ok': 'pong'}}, 0)]:
            rows, _, _ = run_response(mapping, code)
            self.assertNotIn('reply_rejection', rows[-1])
            for row in rows:
                with self.assertRaises(B.InvalidDiagnostics):
                    B.decode_record(json.dumps(dict(row, reply_rejection='invalid_payload')))

    def test_november_19_records_remain_readable(self):
        evidence = json.loads((HERE.parent / 'structured-celery-restoration-results.json').read_text())
        records = evidence['terminal_status']['backend_receipts'][0]['records']
        stream = B.RecordStream()
        for record in records:
            stream.append(json.dumps(record).encode())
        self.assertEqual(stream.records, records)
        self.assertNotIn('reply_rejection', stream.records[-1])
        self.assertFalse(stream.records[-1]['reply_output_valid'])

    def test_pipe_rejection_survives_capture_and_receipt(self):
        for payload, expected in [(b'\xff', 'invalid_utf8'), (b'a' * (B.OUTPUT_LIMIT - 1) + 'é'.encode(), 'output_oversized')]:
            for fd in [1, 2]:
                child = B.celery_capture([sys.executable, '-c', f'import os; os.write({fd}, {payload!r})'],
                                         cwd=str(HERE), timeout=2)
                self.assertFalse(child.complete)
                fixture = BackendFixture()
                original = fixture.run
                with patch.object(fixture, 'run', side_effect=lambda args, **kw: child if args[0] == 'celery' else original(args, **kw)):
                    rows, error, text = fixture.execute()
                self.assertIsNotNone(error)
                self.assertEqual(rows[-1]['classification'], 'celery_unclassified_failure')
                self.assertEqual(capture(text, 1)['records'][-1]['reply_rejection'], expected)
