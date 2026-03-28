from __future__ import annotations

from dataclasses import dataclass
import unicodedata


TAG_BLOCK_START = 0xE0000
TAG_BLOCK_END = 0xE007F


@dataclass(frozen=True)
class SanitizedText:
    text: str
    changed: bool


class InputSanitizer:
    """Removes control-like Unicode content before prompt construction."""

    def sanitize(self, raw: str) -> SanitizedText:
        sanitized_chars: list[str] = []
        changed = False

        for char in raw:
            code_point = ord(char)
            if TAG_BLOCK_START <= code_point <= TAG_BLOCK_END:
                changed = True
                continue
            if unicodedata.category(char) == "Cs":
                changed = True
                continue
            sanitized_chars.append(char)

        normalized = unicodedata.normalize("NFC", "".join(sanitized_chars))
        if normalized != raw:
            changed = True

        return SanitizedText(text=normalized, changed=changed)

