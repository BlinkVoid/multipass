from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from multipass.domain.errors import ErrorCode

T = TypeVar("T")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err:
    error: ErrorCode
    message: str


Result = Ok[T] | Err

