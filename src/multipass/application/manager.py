from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

from multipass.application.backends import BackendKind, ChatBackend, SessionHandle
from multipass.domain.chat import ChatMessage, ConversationState, MessageRole, StreamEvent, StreamEventType
from multipass.infrastructure.clipboard_manager import ClipboardManager
from multipass.security.nonce_service import NonceService
from multipass.security.prompt_builder import PreparedPrompt, PromptBuilder, TrustWrapper
from multipass.security.sanitizer import InputSanitizer, SanitizedText


Transformer = Callable[[str], object]


@dataclass(frozen=True)
class PreparedRequest:
    conversation: ConversationState
    sanitized: SanitizedText
    wrapped_input: str
    prompt: PreparedPrompt


class Manager:
    def __init__(
        self,
        clipboard: ClipboardManager,
        prompt_builder: PromptBuilder,
        sanitizer: InputSanitizer,
        trust_wrapper: TrustWrapper,
        nonce_service: NonceService,
        backends: dict[BackendKind, ChatBackend],
        default_backend: BackendKind,
        transformers: dict[str, Transformer] | None = None,
    ) -> None:
        self._clipboard = clipboard
        self._prompt_builder = prompt_builder
        self._sanitizer = sanitizer
        self._trust_wrapper = trust_wrapper
        self._nonce_service = nonce_service
        self._backends = backends
        self._default_backend = default_backend
        self._transformers = transformers or {}
        self._conversations: dict[str, ConversationState] = {}
        self._sessions: dict[str, SessionHandle] = {}
        self._window_backends: dict[str, BackendKind] = {}

    def set_backend(self, window_id: str, backend_kind: BackendKind) -> None:
        self._window_backends[window_id] = backend_kind
        existing_session = self._sessions.get(window_id)
        if existing_session and existing_session.backend_kind != backend_kind:
            del self._sessions[window_id]

    def get_backend(self, window_id: str = "default") -> BackendKind:
        return self._window_backends.get(window_id, self._default_backend)

    def available_clipboard_operations(self) -> tuple[str, ...]:
        return tuple(sorted(self._transformers))

    def clipboard_operations(self) -> dict[str, Transformer]:
        return dict(self._transformers)

    def read_clipboard(self) -> str:
        return self._clipboard.read_text()

    def write_clipboard(self, value: str) -> None:
        self._clipboard.write_text(value)

    def get_conversation(self, window_id: str = "default") -> ConversationState:
        return self._conversations.setdefault(window_id, ConversationState())

    def prepare_ai_request(self, operation: str, raw_input: str, window_id: str = "default") -> PreparedRequest:
        conversation = self.get_conversation(window_id)
        sanitized = self._sanitizer.sanitize(raw_input)
        wrapped = self._trust_wrapper.wrap(sanitized.text)
        nonce = self._nonce_service.create()
        prompt = self._prompt_builder.build(
            operation=operation,
            wrapped_input=wrapped,
            nonce=nonce,
            history=conversation.messages,
        )
        return PreparedRequest(
            conversation=conversation,
            sanitized=sanitized,
            wrapped_input=wrapped,
            prompt=prompt,
        )

    def run_clipboard_operation(self, operation: str) -> object:
        raw_value = self._clipboard.read_text()
        transformer = self._transformers[operation]
        result = transformer(raw_value)
        if hasattr(result, "value"):
            value = result.value
            if isinstance(value, list):
                self._clipboard.write_text("\n".join(str(item) for item in value))
            else:
                self._clipboard.write_text(str(value))
        return result

    def execute_clipboard_operation(self, operation: str, source_text: str) -> object:
        self.write_clipboard(source_text)
        return self.run_clipboard_operation(operation)

    def send_ai_request(
        self,
        operation: str,
        raw_input: str,
        window_id: str = "default",
        backend_kind: BackendKind | None = None,
    ) -> tuple[PreparedPrompt, list[StreamEvent]]:
        prompt, stream = self.stream_ai_request(
            operation=operation,
            raw_input=raw_input,
            window_id=window_id,
            backend_kind=backend_kind,
        )
        return prompt, list(stream)

    def stream_ai_request(
        self,
        operation: str,
        raw_input: str,
        window_id: str = "default",
        backend_kind: BackendKind | None = None,
    ) -> tuple[PreparedPrompt, Iterator[StreamEvent]]:
        prepared = self.prepare_ai_request(operation=operation, raw_input=raw_input, window_id=window_id)
        backend, session = self._resolve_backend(window_id, backend_kind)

        def event_stream() -> Iterator[StreamEvent]:
            events: list[StreamEvent] = []
            for event in backend.stream(session, prepared.prompt, prepared.conversation.messages):
                events.append(event)
                yield event
            self._record_latest_events(window_id, events)
            prepared.conversation.add(ChatMessage(role=MessageRole.USER, content=prepared.sanitized.text, trusted=False))
            assistant_text = self._collect_assistant_text(events)
            if assistant_text:
                prepared.conversation.add(ChatMessage(role=MessageRole.ASSISTANT, content=assistant_text, trusted=True))

        return prepared.prompt, event_stream()

    def _resolve_backend(
        self,
        window_id: str,
        backend_kind: BackendKind | None,
    ) -> tuple[ChatBackend, SessionHandle]:
        selected_backend = backend_kind or self._window_backends.get(window_id, self._default_backend)
        backend = self._backends[selected_backend]
        session = self._sessions.get(window_id)
        if session is None or session.backend_kind != selected_backend:
            session = backend.start_session()
            self._sessions[window_id] = session
        self._window_backends[window_id] = selected_backend
        return backend, session

    def approve(
        self,
        approval_id: str,
        decision: bool,
        window_id: str = "default",
    ) -> list[StreamEvent]:
        session = self._sessions[window_id]
        backend = self._backends[session.backend_kind]
        approval_events = [
            event
            for event in self._latest_events(window_id)
            if event.type is StreamEventType.APPROVAL_REQUIRED and event.approval is not None
        ]
        matching = next(event.approval for event in approval_events if event.approval.id == approval_id)
        events = list(backend.approve(session, matching, decision))
        self._record_latest_events(window_id, events)
        return events

    def _collect_assistant_text(self, events: list[StreamEvent]) -> str:
        token_text = "".join(event.text for event in events if event.type is StreamEventType.TOKEN)
        if token_text:
            return token_text
        return "".join(event.text for event in events if event.type is StreamEventType.COMPLETED)

    def _latest_events(self, window_id: str) -> list[StreamEvent]:
        return getattr(self, "_event_log", {}).get(window_id, [])

    def _record_latest_events(self, window_id: str, events: list[StreamEvent]) -> None:
        if not hasattr(self, "_event_log"):
            self._event_log: dict[str, list[StreamEvent]] = {}
        self._event_log[window_id] = events
