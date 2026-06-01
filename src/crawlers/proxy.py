from __future__ import annotations

import random
from typing import Optional


class ProxyManager:
    """代理管理器，支持多代理轮换"""

    def __init__(self, proxies: Optional[list[dict]] = None):
        self._proxies = proxies or []
        self._current_index = 0

    @classmethod
    def from_settings(cls, http: Optional[str] = None, https: Optional[str] = None) -> ProxyManager:
        proxies = []
        if http or https:
            entry = {}
            if http:
                entry["http"] = http
            if https:
                entry["https"] = https
            proxies.append(entry)
        return cls(proxies)

    def add_proxy(self, proxy: dict):
        self._proxies.append(proxy)

    def get_next(self) -> Optional[dict]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._proxies)
        return proxy

    def get_random(self) -> Optional[dict]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    @property
    def count(self) -> int:
        return len(self._proxies)

    def remove(self, proxy: dict):
        if proxy in self._proxies:
            self._proxies.remove(proxy)
