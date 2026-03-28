from __future__ import annotations

import base64
from urllib.parse import quote, unquote

from multipass.domain.result import Ok, Result
from multipass.domain.transformers.encoding import decode_base64
from multipass.domain.transformers.text import normalize_whitespace
from multipass.domain.transformers.url import extract_hostname


def encode_base64(value: str) -> Result[str]:
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    return Ok(encoded)


def url_encode(value: str) -> Result[str]:
    return Ok(quote(value, safe=""))


def url_decode(value: str) -> Result[str]:
    return Ok(unquote(value))


CLIPBOARD_OPERATIONS = {
    "normalize_whitespace": normalize_whitespace,
    "extract_hostname": extract_hostname,
    "decode_base64": decode_base64,
    "encode_base64": encode_base64,
    "url_encode": url_encode,
    "url_decode": url_decode,
}
