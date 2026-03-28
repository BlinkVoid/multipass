from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    PARSE_ERROR = "PARSE_ERROR"
    ENCODING_ERROR = "ENCODING_ERROR"
    NO_MATCHES = "NO_MATCHES"

