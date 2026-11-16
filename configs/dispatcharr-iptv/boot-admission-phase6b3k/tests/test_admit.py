"""Offline clock/proc fixtures and unit composition; no daemon or Docker access."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
BASE = HERE.parent / "minimal-phase6b3d/units/dispatcharr-stack.service"
spec = importlib.util.spec_from_file_location("admission_candidate", HERE / "admit.py")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


class Clock:
    def __init__(self):
        self.now = 0
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def snapshots(trace):
    """Repeat the last sample indefinitely; trace entries are idle, steal, load."""
    counters = [0] * 8
    yield gate.Snapshot(tuple(counters), 4, 0)
    i = 0
    while True:
        idle, steal, load = trace[min(i, len(trace) - 1)]
        delta = [100000 - round(idle * 1000) - round(steal * 1000), 0, 0,
                 round(idle * 1000), 0, 0, 0, round(steal * 1000)]
        counters = [a + b for a, b in zip(counters, delta)]
        yield gate.Snapshot(tuple(counters), 4, load)
        i += 1


def run_trace(trace, policy=None):
    clock, events, rows = Clock(), [], snapshots(trace)
    result = gate.admit(policy or gate.Policy(), lambda: next(rows),
                        clock, clock.sleep, events.append)
    return result, clock, events


def proc(counters="100 0 100 600 0 0 0 200", cpus=4):
    return "cpu  " + counters + "\n" + "\n".join(
        f"cpu{i} 1 1 1 1 1 1 1 1" for i in range(cpus))


class ResourceTests(unittest.TestCase):
    def test_settled_host_requires_three_full_intervals(self):
        code, clock, events = run_trace([(80, 2, .7)])
        self.assertEqual(code, 0)
        self.assertEqual(clock.waits, [5, 5, 5])
        self.assertEqual(events[-1]["event"], "capacity_ready")

    def test_phase3j_prestart_values_admit(self):
        code, clock, _ = run_trace([(89.155, 3.397, .53),
                                   (91.610, 1.683, .61),
                                   (88.953, 2.762, .52)])
        self.assertEqual((code, clock.now), (0, 15))

    def test_failed_boot_like_trace_never_admits(self):
        code, clock, events = run_trace([(.107, 25.808, 42.283)])
        self.assertEqual((code, clock.now), (1, 300))
        self.assertFalse(any(e["event"] == "capacity_ready" for e in events))
        self.assertLessEqual(len(events), 62)

    def test_each_condition_independently_blocks(self):
        for row in [(49.9, 1, .5), (70, 10.1, .5), (80, 1, 4)]:
            with self.subTest(row=row):
                code, clock, _ = run_trace([row])
                self.assertEqual((code, clock.now), (1, 300))

    def test_inclusive_idle_and_steal_exclusive_load_boundaries(self):
        self.assertEqual(run_trace([(50, 10, 3.999)])[0], 0)

    def test_bad_sample_resets_streak(self):
        _, clock, events = run_trace([(80, 1, .5), (80, 1, .5),
                                     (10, 20, 10), (80, 1, .5)])
        self.assertEqual(clock.now, 30)
        self.assertEqual([e["streak"] for e in events if e["event"] == "sample"],
                         [1, 2, 0, 1, 2, 3])

    def test_busy_then_settled_is_condition_based_not_fixed_delay(self):
        code, clock, _ = run_trace([(1, 30, 30)] * 6 + [(90, 1, .5)])
        self.assertEqual((code, clock.now), (0, 45))

    def test_deadline_does_not_reset_on_bad_samples(self):
        trace = [(80, 1, .5), (5, 20, 20)] * 30
        code, clock, _ = run_trace(trace)
        self.assertEqual((code, clock.now), (1, 300))

    def test_success_exactly_at_deadline_is_rejected(self):
        code, clock, _ = run_trace([(80, 1, .5)], gate.Policy(max_wait=15))
        self.assertEqual((code, clock.now), (1, 15))

    def test_oversleep_cannot_admit_late(self):
        clock, events, rows = Clock(), [], snapshots([(80, 1, .5)])
        def delayed_sleep(seconds):
            clock.sleep(seconds + 350)
        code = gate.admit(reader=lambda: next(rows), clock=clock,
                          sleep=delayed_sleep, emit=events.append)
        self.assertEqual(code, 1)
        self.assertFalse(any(e["event"] == "capacity_ready" for e in events))

    def test_reader_or_logging_delay_cannot_admit_late(self):
        for delayed in ["reader", "logging", "decision_logging"]:
            with self.subTest(delayed=delayed):
                clock, events, rows = Clock(), [], snapshots([(80, 1, .5)])
                count = [0]
                def reader():
                    count[0] += 1
                    value = next(rows)
                    if delayed == "reader" and count[0] == 4:
                        clock.now += 350
                    return value
                def emit(event):
                    events.append(event)
                    if delayed == "logging" and event.get("streak") == 3:
                        clock.now += 350
                    if delayed == "decision_logging" and event["event"] == "capacity_ready":
                        clock.now += 350
                self.assertEqual(gate.admit(reader=reader, clock=clock,
                                           sleep=clock.sleep, emit=emit), 1)

    def test_telemetry_failure_initial_or_mid_wait(self):
        for fail_at in [1, 3]:
            clock, rows, events, calls = Clock(), snapshots([(80, 1, .5)]), [], [0]
            def reader():
                calls[0] += 1
                if calls[0] == fail_at:
                    raise gate.TelemetryError("telemetry_unreadable")
                return next(rows)
            self.assertEqual(gate.admit(reader=reader, clock=clock,
                                       sleep=clock.sleep, emit=events.append), 2)
            self.assertFalse(any(e["event"] == "capacity_ready" for e in events))

    def test_initial_and_changed_cpu_topology_fail(self):
        for at in [1, 3]:
            clock, rows, calls = Clock(), snapshots([(80, 1, .5)]), [0]
            def reader():
                calls[0] += 1
                value = next(rows)
                return gate.Snapshot(value.counters, 8, value.load1) if calls[0] == at else value
            self.assertEqual(gate.admit(reader=reader, clock=clock,
                                       sleep=clock.sleep, emit=lambda _: None), 2)

    def test_counter_decrease_discards_sample_and_resets_streak(self):
        clock, events = Clock(), []
        rows = iter([gate.Snapshot((0, 0, 0, 0, 20, 0, 0, 0), 4, .5),
                     gate.Snapshot((10, 0, 0, 80, 21, 0, 0, 1), 4, .5),
                     gate.Snapshot((20, 0, 0, 160, 19, 0, 0, 2), 4, .5),
                     gate.Snapshot((30, 0, 0, 240, 20, 0, 0, 3), 4, .5),
                     gate.Snapshot((40, 0, 0, 320, 21, 0, 0, 4), 4, .5),
                     gate.Snapshot((50, 0, 0, 400, 22, 0, 0, 5), 4, .5)])
        self.assertEqual(gate.admit(reader=lambda: next(rows), clock=clock,
                                   sleep=clock.sleep, emit=events.append), 0)
        self.assertEqual(clock.now, 25)
        self.assertEqual(sum(e["event"] == "sample_invalid" for e in events), 1)

    def test_frozen_counters_cannot_admit(self):
        clock, value = Clock(), gate.Snapshot((1,) * 8, 4, .5)
        self.assertEqual(gate.admit(reader=lambda: value, clock=clock,
                                   sleep=clock.sleep, emit=lambda _: None), 1)
        self.assertEqual(clock.now, 300)

    def test_keyboard_cancellation_cannot_admit(self):
        clock = Clock()
        def cancel(_):
            raise KeyboardInterrupt
        self.assertEqual(gate.admit(reader=lambda: next(snapshots([(80, 1, .5)])),
                                   clock=clock, sleep=cancel, emit=lambda _: None), 130)

    def test_gate_exits_and_does_not_supervise_after_admission(self):
        code, clock, events = run_trace([(80, 1, .5)] * 3 + [(0, 50, 50)])
        self.assertEqual((code, clock.now), (0, 15))
        self.assertEqual(events[-1]["event"], "capacity_ready")


class ParsingTests(unittest.TestCase):
    def test_proc_cpu_modes_and_guest_double_count(self):
        s = gate.parse_snapshot(proc("100 0 100 600 0 0 0 200 80 0"), ".5 1 2 1/1 99")
        a = gate.Snapshot((0,) * 8, 4, .5)
        self.assertEqual(gate.percentages(a, s), (60, 20))

    def test_malformed_missing_nonfinite_or_negative_inputs(self):
        pairs = [("", ".5"), (proc("1 2 3"), ".5"), (proc("x 1 1 1 1 1 1 1"), ".5"),
                 (proc("-1 1 1 1 1 1 1 1"), ".5"), (proc(), ""),
                 (proc(), "nan"), (proc(), "inf"), (proc(), "-1"),
                 (proc(cpus=0), ".5")]
        for stat, load in pairs:
            with self.subTest(stat=stat[:20], load=load):
                with self.assertRaises(gate.TelemetryError):
                    gate.parse_snapshot(stat, load)

    def test_fixed_proc_paths_and_io_error(self):
        with patch.object(gate.Path, "read_text", side_effect=[proc(), ".5"]) as read:
            self.assertEqual(gate.read_snapshot().cpus, 4)
            self.assertEqual(read.call_count, 2)
        with patch.object(gate.Path, "read_text", side_effect=OSError("private detail")):
            with self.assertRaisesRegex(gate.TelemetryError, "^telemetry_unreadable$"):
                gate.read_snapshot()

    def test_policy_errors(self):
        for kwargs in [dict(max_wait=0), dict(interval=0), dict(interval=300),
                       dict(idle_min=101), dict(steal_max=-1), dict(load_max=float("nan")),
                       dict(consecutive=0), dict(expected_cpus=0)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                gate.Policy(**kwargs)

    def test_unexpected_cli_arguments_refused(self):
        with patch.object(gate.sys, "argv", ["admit.py", "--bypass"]), patch.object(gate, "emit_json"):
            self.assertEqual(gate.main(), 2)

    def test_telemetry_log_allowlist(self):
        _, _, events = run_trace([(80, 1, .5)])
        fields = {"event", "elapsed_s", "max_wait_s", "interval_s", "consecutive",
                  "idle_min_pct", "steal_max_pct", "load1_below", "expected_cpus",
                  "idle_pct", "steal_pct", "load1", "streak", "reason"}
        self.assertTrue(all(set(e) <= fields for e in events))
        self.assertNotIn("http", json.dumps(events))


def service_directives(text):
    values = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            section = line
        elif section == "[Service]" and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            if value:
                values.setdefault(key, []).append(value)
            else:
                values[key] = []
    return values


class UnitTests(unittest.TestCase):
    def setUp(self):
        self.base = BASE.read_text()
        self.drop = (HERE / "20-resource-admission.conf").read_text()

    def test_reviewed_base_is_unchanged(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),
                         "30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e")

    def test_effective_prestart_order_preserves_every_original_check(self):
        before = service_directives(self.base)
        after = service_directives(self.base + "\n" + self.drop)
        self.assertEqual(after["ExecStartPre"][0], before["ExecStartPre"][0])
        self.assertTrue(after["ExecStartPre"][1].endswith("boot-admission-phase6b3k/admit.py"))
        self.assertEqual(after["ExecStartPre"][2:], before["ExecStartPre"][1:])
        self.assertEqual(set(service_directives(self.drop)), {"ExecStartPre"})
        for k in before.keys() - {"ExecStartPre"}:
            self.assertEqual(after[k], before[k])

    def test_native_dependencies_health_and_timeouts_unchanged(self):
        self.assertNotIn("[Unit]", self.drop)
        values = service_directives(self.base + "\n" + self.drop)
        self.assertEqual(values["TimeoutStartSec"], ["540"])
        self.assertEqual(values["TimeoutStopSec"], ["240"])
        self.assertEqual(values["Restart"], ["no"])
        self.assertIn("--wait-timeout 360", values["ExecStart"][0])
        self.assertIn(" stop --timeout 60 gateway dispatcharr iptv-vpn", values["ExecStopPost"][0])

    def test_failure_path_model_blocks_later_commands(self):
        # Model only: actual ExecStartPre/ExecStopPost semantics are documented
        # by systemd 255, not demonstrated by a running test service here.
        commands = service_directives(self.base + "\n" + self.drop)["ExecStartPre"]
        for fail_index in range(len(commands)):
            executed = []
            for i, cmd in enumerate(commands):
                executed.append(cmd)
                if i == fail_index:
                    executed.append("scoped-stop")
                    break
            self.assertEqual(len(executed), fail_index + 2)
            self.assertEqual(executed[-1], "scoped-stop")
            self.assertNotIn("up --detach", " ".join(executed))

    def test_helper_has_no_external_control_imports(self):
        tree = ast.parse((HERE / "admit.py").read_text())
        imports = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)}
        imports |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(imports, {"dataclasses", "json", "math", "pathlib", "sys", "time"})


if __name__ == "__main__":
    unittest.main()
