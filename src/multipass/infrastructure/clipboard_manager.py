from __future__ import annotations


class ClipboardManager:
    def __init__(self) -> None:
        self._value = ""

    def read_text(self) -> str:
        return self._value

    def write_text(self, value: str) -> None:
        self._value = value

