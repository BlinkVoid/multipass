from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import secrets


@dataclass(frozen=True)
class NonceBundle:
    request_nonce: str
    time_marker: str


class NonceService:
    def create(self) -> NonceBundle:
        nonce = secrets.token_urlsafe(18)
        offset_seconds = secrets.randbelow(600)
        time_marker = (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()
        return NonceBundle(request_nonce=nonce, time_marker=time_marker)

