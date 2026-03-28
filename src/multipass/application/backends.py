from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable

from multipass.domain.chat import ApprovalRequest, ChatMessage, StreamEvent
from multipass.security.prompt_builder import PreparedPrompt


class BackendKind(StrEnum):
    BEDROCK = "bedrock"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"
    CLAUDE_CODE_CLI = "claude_code_cli"
    CODEX_CLI = "codex_cli"


@dataclass(frozen=True)
class BackendCapabilities:
    streaming: bool
    approvals: bool
    file_actions: bool
    session_reuse: bool
    structured_output: bool


@dataclass(frozen=True)
class BackendConfig:
    kind: BackendKind
    model: str
    endpoint: str | None = None
    api_key_env: str | None = None
    executable: str | None = None
    args: tuple[str, ...] = ()
    workspace: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionHandle:
    id: str
    backend_kind: BackendKind
    model: str


class ChatBackend(ABC):
    def __init__(self, config: BackendConfig) -> None:
        self.config = config

    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    @abstractmethod
    def start_session(self) -> SessionHandle:
        raise NotImplementedError

    @abstractmethod
    def stream(
        self,
        session: SessionHandle,
        prompt: PreparedPrompt,
        history: list[ChatMessage],
    ) -> Iterable[StreamEvent]:
        raise NotImplementedError

    def cancel(self, session: SessionHandle) -> None:
        _ = session

    def approve(self, session: SessionHandle, approval: ApprovalRequest, decision: bool) -> Iterable[StreamEvent]:
        _ = session
        _ = approval
        _ = decision
        return []

