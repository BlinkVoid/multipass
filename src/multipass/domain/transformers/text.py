from multipass.domain.errors import ErrorCode
from multipass.domain.result import Err, Ok, Result


def normalize_whitespace(value: str) -> Result[str]:
    if not value.strip():
        return Err(ErrorCode.INVALID_INPUT, "Input text is empty.")
    collapsed = " ".join(value.split())
    return Ok(collapsed)

