"""In-process WebSocket fan-out.

Staff connections receive operational events; a tourist connection only
receives events addressed to that tourist. One backend instance is assumed
(Render free tier); multiple instances would need Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from fastapi import WebSocket

log = logging.getLogger("app.realtime")


@dataclass(eq=False)
class Connection:
    websocket: WebSocket
    role: str
    subject: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=200))


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[Connection] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def register(self, conn: Connection) -> None:
        self.loop = asyncio.get_running_loop()
        self.connections.add(conn)

    def unregister(self, conn: Connection) -> None:
        self.connections.discard(conn)

    def stats(self) -> dict:
        return {
            "connections": len(self.connections),
            "staff": sum(1 for c in self.connections if c.role != "TOURIST"),
            "tourists": sum(1 for c in self.connections if c.role == "TOURIST"),
        }

    def _deliver(self, event: dict, staff: bool, tourist_code: str | None) -> None:
        message = json.dumps(event, default=str)
        for conn in list(self.connections):
            wanted = (staff and conn.role != "TOURIST") or (
                tourist_code is not None and conn.role == "TOURIST" and conn.subject == tourist_code
            )
            if not wanted:
                continue
            try:
                conn.queue.put_nowait(message)
            except asyncio.QueueFull:
                log.warning("Dropping event for slow websocket client %s", conn.subject)

    def publish(self, event_type: str, data: dict, staff: bool = True, tourist_code: str | None = None) -> None:
        """Thread-safe: callable from sync route handlers (run in a threadpool)."""
        event = {"type": event_type, "data": data}
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            self._deliver(event, staff, tourist_code)
        else:
            loop.call_soon_threadsafe(self._deliver, event, staff, tourist_code)


manager = ConnectionManager()
