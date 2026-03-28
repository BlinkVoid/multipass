from multipass.application.backends import BackendConfig, BackendKind
from multipass.application.manager import Manager
from multipass.domain.chat import ApprovalRequest, StreamEvent, StreamEventType
from multipass.infrastructure.backends import ClaudeCodeCliBackend, OpenAICompatibleBackend
from multipass.infrastructure.clipboard_manager import ClipboardManager
from multipass.security.nonce_service import NonceService
from multipass.security.prompt_builder import PromptBuilder, TrustWrapper
from multipass.security.sanitizer import InputSanitizer


def test_manager_routes_raw_input_through_security_pipeline_and_updates_conversation() -> None:
    clipboard = ClipboardManager()
    backend = OpenAICompatibleBackend(
        config=BackendConfig(kind=BackendKind.DEEPSEEK, model="deepseek-chat"),
        transport=lambda payload: [
            StreamEvent(type=StreamEventType.TOKEN, text="safe "),
            StreamEvent(type=StreamEventType.TOKEN, text="answer", metadata={"model": payload["model"]}),
        ],
    )
    manager = Manager(
        clipboard=clipboard,
        prompt_builder=PromptBuilder(),
        sanitizer=InputSanitizer(),
        trust_wrapper=TrustWrapper(),
        nonce_service=NonceService(),
        backends={BackendKind.DEEPSEEK: backend},
        default_backend=BackendKind.DEEPSEEK,
    )

    prompt, events = manager.send_ai_request("classify", "hello\U000E0001world")

    assert "<untrusted_input>" in prompt.user_prompt
    assert "helloworld" in prompt.user_prompt
    assert "\U000E0001" not in prompt.user_prompt
    assert "".join(event.text for event in events if event.type is StreamEventType.TOKEN) == "safe answer"
    conversation = manager.get_conversation()
    assert conversation.messages[0].content == "helloworld"
    assert conversation.messages[1].content == "safe answer"


def test_manager_approval_round_trip_uses_backend() -> None:
    approval = ApprovalRequest(id="approval-1", kind="shell", summary="Run ls", command="ls")
    cli_backend = ClaudeCodeCliBackend(
        config=BackendConfig(kind=BackendKind.CLAUDE_CODE_CLI, model="claude-code"),
        runner=lambda invocation: [
            StreamEvent(type=StreamEventType.APPROVAL_REQUIRED, approval=approval),
            StreamEvent(type=StreamEventType.TOKEN, text=invocation.executable),
        ],
    )
    manager = Manager(
        clipboard=ClipboardManager(),
        prompt_builder=PromptBuilder(),
        sanitizer=InputSanitizer(),
        trust_wrapper=TrustWrapper(),
        nonce_service=NonceService(),
        backends={BackendKind.CLAUDE_CODE_CLI: cli_backend},
        default_backend=BackendKind.CLAUDE_CODE_CLI,
    )

    _, events = manager.send_ai_request("chat", "check status")
    manager._record_latest_events("default", events)
    approval_events = manager.approve("approval-1", True)

    assert events[0].approval == approval
    assert approval_events[0].text == "approval_approved"
    assert cli_backend.last_approval == (approval, True)
