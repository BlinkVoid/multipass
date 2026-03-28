from __future__ import annotations

from collections.abc import Iterable


class StreamWorker:
    def run(self, chunks: Iterable[str]) -> str:
        return "".join(chunks)

