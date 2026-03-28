from urllib.parse import urlparse

from multipass.domain.errors import ErrorCode
from multipass.domain.result import Err, Ok, Result


def extract_hostname(value: str) -> Result[str]:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return Err(ErrorCode.PARSE_ERROR, "Input is not a valid URL.")
    return Ok(parsed.netloc)

