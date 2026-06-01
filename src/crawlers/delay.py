from __future__ import annotations

import random
import time
from collections import deque


class AdaptiveDelayController:
    """自适应延迟控制器，根据请求成功率动态调整延迟时间"""

    def __init__(self, delay_min: float = 2.5, delay_max: float = 5.0, window_size: int = 20):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.window_size = window_size
        self._history: deque[bool] = deque(maxlen=window_size)
        self._current_delay = delay_min

    @property
    def success_rate(self) -> float:
        if not self._history:
            return 1.0
        return sum(self._history) / len(self._history)

    def record(self, success: bool):
        self._history.append(success)
        rate = self.success_rate
        if rate < 0.7:
            self._current_delay = min(self._current_delay * 1.5, self.delay_max)
        elif rate > 0.95 and self._current_delay > self.delay_min:
            self._current_delay = max(self._current_delay * 0.9, self.delay_min)

    def wait(self):
        jitter = random.uniform(-0.3, 0.3)
        sleep_time = max(0.5, self._current_delay + jitter)
        time.sleep(sleep_time)

    def reset(self):
        self._history.clear()
        self._current_delay = self.delay_min
