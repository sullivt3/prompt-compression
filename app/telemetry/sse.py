"""Bounded SSE usage inspection; callers forward the original bytes unchanged."""

import json
from typing import Any


class SSEUsageCollector:
    def __init__(self, max_frame_bytes: int = 65536) -> None:
        self.max_frame_bytes = max_frame_bytes
        self.usage: dict[str, Any] | None = None
        self._line = bytearray()
        self._data: list[bytes] = []
        self._size = 0
        self._discard = False
        self._after_cr = False

    def feed(self, chunk: bytes) -> None:
        for byte in chunk:
            if self._after_cr:
                self._after_cr = False
                if byte == 10:
                    continue
            if byte in (10, 13):
                self._finish_line()
                self._after_cr = byte == 13
            else:
                self._size += 1
                if self._size > self.max_frame_bytes:
                    self._discard = True
                    self._data.clear()
                    # Retain only whether this line is empty, never its oversized content.
                    self._line[:] = b"x"
                elif not self._discard:
                    self._line.append(byte)
                elif not self._line:
                    self._line.append(120)

    def _finish_line(self) -> None:
        line = bytes(self._line)
        self._line.clear()
        if not line:
            if not self._discard and self._data:
                try:
                    event = json.loads(b"\n".join(self._data))
                    if isinstance(event, dict) and isinstance(event.get("usage"), dict):
                        self.usage = event["usage"]
                except (ValueError, UnicodeError):
                    pass
            self._data.clear()
            self._size = 0
            self._discard = False
        elif not self._discard and line.startswith(b"data:"):
            value = line[5:]
            self._data.append(value[1:] if value.startswith(b" ") else value)
