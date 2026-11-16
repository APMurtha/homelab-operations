#!/usr/bin/env python3
"""UNAPPLIED: bounded CPU admission, not application or security supervision.

Reads only /proc/stat and /proc/loadavg. Never invokes Docker, nft or systemd.
No daemon, state file, network call, signal, or application data access.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
import time


@dataclass(frozen=True)
class Policy:
    max_wait: float = 300
    interval: float = 5
    consecutive: int = 3
    idle_min: float = 50
    steal_max: float = 10
    load_max: float = 4
    expected_cpus: int = 4

    def __post_init__(self):
        values = (self.max_wait, self.interval, self.idle_min,
                  self.steal_max, self.load_max)
        if (not all(math.isfinite(v) for v in values)
                or not 0 < self.interval < self.max_wait
                or self.consecutive < 1 or self.expected_cpus < 1
                or not 0 <= self.idle_min <= 100
                or not 0 <= self.steal_max <= 100 or self.load_max <= 0):
            raise ValueError("invalid_policy")


@dataclass(frozen=True)
class Snapshot:
    counters: tuple
    cpus: int
    load1: float


class TelemetryError(ValueError):
    pass


def parse_snapshot(stat, load):
    lines = stat.splitlines()
    if not lines or not lines[0].startswith("cpu "):
        raise TelemetryError("missing_cpu_aggregate")
    fields = lines[0].split()[1:]
    try:
        if len(fields) < 8:
            raise ValueError
        # guest/guest_nice are already included in user/nice: do not add twice.
        counters = tuple(int(v) for v in fields[:8])
        load1 = float(load.split()[0])
    except (ValueError, IndexError):
        raise TelemetryError("malformed_telemetry") from None
    cpus = sum(line.split()[0][3:].isdigit() for line in lines
               if line.startswith("cpu") and line.split())
    if min(counters) < 0 or not math.isfinite(load1) or load1 < 0 or cpus < 1:
        raise TelemetryError("invalid_telemetry")
    return Snapshot(counters, cpus, load1)


def read_snapshot():
    try:
        return parse_snapshot(Path("/proc/stat").read_text(),
                              Path("/proc/loadavg").read_text())
    except OSError:
        raise TelemetryError("telemetry_unreadable") from None


def percentages(previous, current):
    delta = [b - a for a, b in zip(previous.counters, current.counters)]
    # In particular, Linux documents that iowait can decrease. Discard such a
    # sample and require a fresh full streak; never clamp it into a pass.
    if any(v < 0 for v in delta) or sum(delta) <= 0:
        return None
    total = sum(delta)
    return 100 * delta[3] / total, 100 * delta[7] / total


def emit_json(event):
    print(json.dumps(event, sort_keys=True), flush=True)


def admit(policy=Policy(), reader=read_snapshot, clock=time.monotonic,
          sleep=time.sleep, emit=emit_json):
    start = clock()
    deadline = start + policy.max_wait
    streak = 0

    def event(kind, **fields):
        emit({"event": kind, "elapsed_s": round(clock() - start, 3), **fields})

    def snapshot():
        value = reader()
        if value.cpus != policy.expected_cpus:
            raise TelemetryError("cpu_topology_mismatch")
        return value

    try:
        event("waiting", max_wait_s=policy.max_wait,
              interval_s=policy.interval, consecutive=policy.consecutive,
              idle_min_pct=policy.idle_min, steal_max_pct=policy.steal_max,
              load1_below=policy.load_max, expected_cpus=policy.expected_cpus)
        previous = snapshot()
        while True:
            remaining = deadline - clock()
            if remaining <= 0:
                event("blocked", reason="admission_deadline")
                return 1
            # Measurement interval only: there is no unconditional boot delay.
            sleep(min(policy.interval, remaining))
            if clock() >= deadline:
                event("blocked", reason="admission_deadline")
                return 1
            current = snapshot()
            if clock() >= deadline:
                event("blocked", reason="admission_deadline")
                return 1
            result = percentages(previous, current)
            previous = current
            if result is None:
                streak = 0
                event("sample_invalid", reason="counter_discontinuity")
                continue
            idle, steal = result
            qualifies = (idle >= policy.idle_min and steal <= policy.steal_max
                         and current.load1 < policy.load_max)
            streak = streak + 1 if qualifies else 0
            event("sample", idle_pct=round(idle, 3),
                  steal_pct=round(steal, 3), load1=current.load1, streak=streak)
            if streak >= policy.consecutive:
                # Do not admit late if output/processing was descheduled.
                if clock() >= deadline:
                    event("blocked", reason="admission_deadline")
                    return 1
                # A capacity observation is not authorization until exit 0.
                # stdout may itself block while journald is under pressure.
                event("capacity_ready")
                if clock() >= deadline:
                    event("blocked", reason="admission_deadline")
                    return 1
                return 0
    except TelemetryError as exc:
        event("blocked", reason=str(exc))
        return 2
    except KeyboardInterrupt:
        event("blocked", reason="interrupted")
        return 130


def main():
    if len(sys.argv) != 1:
        emit_json({"event": "blocked", "reason": "unexpected_arguments"})
        return 2
    return admit()


if __name__ == "__main__":
    sys.exit(main())
