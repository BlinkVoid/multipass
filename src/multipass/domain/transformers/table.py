from multipass.domain.errors import ErrorCode
from multipass.domain.result import Err, Ok, Result


def csv_to_lines(value: str) -> Result[list[str]]:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return Err(ErrorCode.NO_MATCHES, "No rows found in table input.")
    return Ok(lines)

