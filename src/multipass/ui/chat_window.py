from dataclasses import dataclass, field
from enum import StrEnum

from multipass.application.backends import BackendKind
from multipass.domain.chat import ApprovalRequest, ConversationState, StreamEvent, StreamEventType


class WindowStatus(StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    FINISHED = "finished"


@dataclass
class ChatWindow:
    id: str = "default"
    backend_kind: BackendKind = BackendKind.DEEPSEEK
    model: str = ""
    status: WindowStatus = WindowStatus.IDLE
    transcript: list[str] = field(default_factory=list)
    activity_feed: list[str] = field(default_factory=list)
    pending_approvals: list[ApprovalRequest] = field(default_factory=list)
    conversation: ConversationState = field(default_factory=ConversationState)

    def append_message(self, message: str) -> None:
        self.transcript.append(message)

    def apply_event(self, event: StreamEvent) -> None:
        if event.type is StreamEventType.TOKEN:
            if self.status is not WindowStatus.STREAMING:
                self.status = WindowStatus.STREAMING
                self.transcript.append("")
            self.transcript[-1] = f"{self.transcript[-1]}{event.text}"
            return

        if event.type is StreamEventType.APPROVAL_REQUIRED and event.approval is not None:
            self.pending_approvals.append(event.approval)
            self.activity_feed.append(event.approval.summary)
            self.status = WindowStatus.WAITING_APPROVAL
            return

        if event.type is StreamEventType.STATUS:
            self.activity_feed.append(event.text)
            if event.text.startswith("approval_"):
                self.pending_approvals.clear()
                self.status = WindowStatus.STREAMING
            return

        if event.type is StreamEventType.STDERR:
            self.activity_feed.append(event.text)
            return

        if event.type is StreamEventType.ERROR:
            self.activity_feed.append(event.text)
            self.status = WindowStatus.ERROR
            return

        if event.type is StreamEventType.COMPLETED:
            if self.status is not WindowStatus.STREAMING:
                self.transcript.append(event.text)
            self.status = WindowStatus.FINISHED
