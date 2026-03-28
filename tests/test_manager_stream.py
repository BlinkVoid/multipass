from multipass.application.backends import BackendConfig, BackendKind
from multipass.application.manager import Manager
from multipass.domain.chat import StreamEvent, StreamEventType
from multipass.infrastructure.backends import OpenAICompatibleBackend
from multipass.infrastructure.clipboard_manager import ClipboardManager
from multipass.security.nonce_service import NonceService
from multipass.security.prompt_builder import PromptBuilder, TrustWrapper
from multipass.security.sanitizer import InputSanitizer


def test_stream_ai_request_updates_conversation_after_stream_consumption() -> None:
    backend = OpenAICompatibleBackend(
        config=BackendConfig(kind=BackendKind.DEEPSEEK, model="deepseek-chat"),
        transport=lambda payload: [
            StreamEvent(type=StreamEventType.TOKEN, text="streamed ", metadata={"model": payload["model"]}),
            StreamEvent(type=StreamEventType.TOKEN, text="reply"),
            StreamEvent(type=StreamEventType.COMPLETED, text=""),
        ],
    )
    manager = Manager(
        clipboard=ClipboardManager(),
        prompt_builder=PromptBuilder(),
        sanitizer=InputSanitizer(),
        trust_wrapper=TrustWrapper(),
        nonce_service=NonceService(),
        backends={BackendKind.DEEPSEEK: backend},
        default_backend=BackendKind.DEEPSEEK,
    )

    prompt, stream = manager.stream_ai_request("chat", "hello")
    events = list(stream)

    assert prompt.operation == "chat"
    assert "".join(event.text for event in events if event.type is StreamEventType.TOKEN) == "streamed reply"
    conversation = manager.get_conversation()
    assert conversation.messages[0].content == "hello"
    assert conversation.messages[1].content == "streamed reply"
