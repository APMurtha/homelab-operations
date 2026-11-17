"""120 attempts per trailing 60 seconds, fixed storage, no retry or wait queue."""
from collections import deque
import threading
import time


class RollingBudget:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.events = deque(maxlen=120)
        self.lock = threading.Lock()

    def take(self):
        with self.lock:
            now = self.clock()
            while self.events and self.events[0] <= now - 60:
                self.events.popleft()
            if len(self.events) == 120:
                raise ValueError('rolling_request_budget')
            self.events.append(now)
