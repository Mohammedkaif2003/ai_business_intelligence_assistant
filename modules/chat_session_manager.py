from __future__ import annotations


class ChatSessionManager:
    """Lightweight session helper for chat state compatibility."""

    def __init__(self):
        self._history = []

    def add(self, role: str, content: str) -> None:
        self._history.append({"role": str(role), "content": str(content)})

    def clear(self) -> None:
        self._history.clear()

    @property
    def history(self):
        return list(self._history)
