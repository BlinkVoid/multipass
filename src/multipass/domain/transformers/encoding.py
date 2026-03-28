import base64

from multipass.domain.errors import ErrorCode
from multipass.domain.result import Err, Ok, Result


def decode_base64(value: str) -> Result[str]:
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return Err(ErrorCode.ENCODING_ERROR, "Unable to decode base64 input.")
    return Ok(decoded)

