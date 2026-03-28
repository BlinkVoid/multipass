from multipass.domain.chat import ChatMessage, MessageRole
from multipass.security.nonce_service import NonceBundle
from multipass.security.prompt_builder import PromptBuilder, TrustWrapper
from multipass.security.prompt_policy import PromptPolicy


def test_prompt_builder_embeds_trusted_tokens_wrapped_input_and_history() -> None:
    wrapper = TrustWrapper()
    builder = PromptBuilder(policy=PromptPolicy.default())
    nonce = NonceBundle(request_nonce="nonce-123", time_marker="2026-03-28T12:00:00+00:00")

    wrapped = wrapper.wrap("suspicious input")
    prompt = builder.build(
        operation="summarize",
        wrapped_input=wrapped,
        nonce=nonce,
        history=[ChatMessage(role=MessageRole.USER, content="previous question", trusted=False)],
    )

    assert "token=mp-sec:nonce-123" in prompt.system_prompt
    assert "time_marker=2026-03-28T12:00:00+00:00" in prompt.system_prompt
    assert "policy name=multipass-core version=v1" in prompt.system_prompt
    assert "<untrusted_input>" in prompt.user_prompt
    assert "suspicious input" in prompt.user_prompt
    assert "<history role=user trust=untrusted>" in prompt.user_prompt
