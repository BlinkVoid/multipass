from datetime import datetime

from multipass.domain.errors import ErrorCode
from multipass.domain.result import Err, Ok, Result


def summarize_range(start: str, end: str) -> Result[str]:
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return Err(ErrorCode.PARSE_ERROR, "Time range must use ISO 8601 values.")
    if end_dt < start_dt:
        return Err(ErrorCode.INVALID_INPUT, "End time cannot be earlier than start time.")
    duration = end_dt - start_dt
    return Ok(f"{duration.total_seconds() / 60:.0f} minutes")

