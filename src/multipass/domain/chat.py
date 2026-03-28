from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str
    trusted: bool = False


@dataclass
class ConversationState:
    messages: list[ChatMessage] = field(default_factory=list)

    def add(self, message: ChatMessage) -> None:
        self.messages.append(message)

    def extend(self, messages: list[ChatMessage]) -> None:
        self.messages.extend(messages)


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    kind: str
    summary: str
    command: str | None = None


class StreamEventType(StrEnum):
    STATUS = "status"
    TOKEN = "token"
    APPROVAL_REQUIRED = "approval_required"
    STDERR = "stderr"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass(frozen=True)
class StreamEvent:
    type: StreamEventType
    text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    approval: ApprovalRequest | None = None

