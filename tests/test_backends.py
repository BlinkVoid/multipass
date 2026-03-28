import json

from multipass.application.backends import BackendConfig, BackendKind
from multipass.domain.chat import ChatMessage, MessageRole
from multipass.infrastructure.backends import (
    BedrockBackend,
    ClaudeCodeCliBackend,
    CodexCliBackend,
    OpenAICompatibleBackend,
)
from multipass.security.nonce_service import NonceBundle
from multipass.security.prompt_builder import PromptBuilder, TrustWrapper


def _prepared_prompt():
    builder = PromptBuilder()
    wrapper = TrustWrapper()
    return builder.build(
        operation="review",
        wrapped_input=wrapper.wrap("payload"),
        nonce=NonceBundle(request_nonce="nonce-1", time_marker="2026-03-28T00:00:00+00:00"),
        history=[ChatMessage(role=MessageRole.ASSISTANT, content="prior answer", trusted=True)],
    )


def test_openai_compatible_backend_formats_messages() -> None:
    backend = OpenAICompatibleBackend(
        config=BackendConfig(kind=BackendKind.DEEPSEEK, model="deepseek-chat"),
    )

    list(backend.stream(backend.start_session(), _prepared_prompt(), []))

    assert backend.last_request is not None
    assert backend.last_request["model"] == "deepseek-chat"
    assert backend.last_request["messages"][0]["role"] == "system"
    assert backend.last_request["messages"][-1]["role"] == "user"


def test_bedrock_backend_formats_system_and_messages() -> None:
    backend = BedrockBackend(
        config=BackendConfig(kind=BackendKind.BEDROCK, model="claude-sonnet"),
        transport=lambda payload: [],
    )

    list(backend.stream(backend.start_session(), _prepared_prompt(), []))

    assert backend.last_request is not None
    assert backend.last_request["modelId"] == "claude-sonnet"
    assert backend.last_request["system"][0]["text"].startswith("[policy")
    assert backend.last_request["messages"][-1]["role"] == "user"


def test_claude_cli_backend_builds_stream_json_invocation() -> None:
    backend = ClaudeCodeCliBackend(
        config=BackendConfig(kind=BackendKind.CLAUDE_CODE_CLI, model="claude-code"),
        runner=lambda invocation: [],
    )

    list(backend.stream(backend.start_session(), _prepared_prompt(), []))

    assert backend.last_invocation is not None
    assert backend.last_invocation.executable == "claude"
    assert "--output-format" in backend.last_invocation.args
    payload = json.loads(backend.last_invocation.input_text)
    assert payload["message"]["content"][0]["type"] == "text"


def test_codex_cli_backend_builds_plain_prompt_invocation() -> None:
    backend = CodexCliBackend(
        config=BackendConfig(kind=BackendKind.CODEX_CLI, model="codex-cli", executable="codex"),
        runner=lambda invocation: [],
    )

    list(backend.stream(backend.start_session(), _prepared_prompt(), []))

    assert backend.last_invocation is not None
    assert backend.last_invocation.executable == "codex"
    assert "Operation: review" in backend.last_invocation.input_text
