# -*- coding: utf-8 -*-
"""应用事件总线：日志缓冲 + WebSocket 广播。"""

from __future__ import annotations

import asyncio
import collections
import time
from typing import Any, Deque, Dict, List, Optional, Set


class EventBus:
    def __init__(self, capacity: int = 500):
        self._history: Deque[Dict[str, Any]] = collections.deque(maxlen=capacity)
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    def publish_sync(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        event = {
            "type": event_type,
            "ts": int(time.time() * 1000),
            **payload,
        }
        self._history.append(event)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except Exception:
                pass
        return event

    async def publish(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        return self.publish_sync(event_type, **payload)

    def history(self, limit: int = 200) -> List[Dict[str, Any]]:
        items = list(self._history)
        if limit <= 0:
            return items
        return items[-limit:]

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.discard(queue)


bus = EventBus()
