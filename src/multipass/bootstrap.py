from __future__ import annotations

from multipass.application.clipboard_operations import CLIPBOARD_OPERATIONS
from multipass.application.backends import BackendKind, ChatBackend
from multipass.application.manager import Manager
from multipass.infrastructure.backends import (
    BedrockBackend,
    ClaudeCodeCliBackend,
    CodexCliBackend,
    OpenAICompatibleBackend,
)
from multipass.infrastructure.clipboard_manager import ClipboardManager
from multipass.infrastructure.config import Config
from multipass.security.nonce_service import NonceService
from multipass.security.prompt_builder import PromptBuilder, TrustWrapper
from multipass.security.sanitizer import InputSanitizer


def build_backends(config: Config) -> dict[BackendKind, ChatBackend]:
    return {
        BackendKind.BEDROCK: BedrockBackend(config.backends[BackendKind.BEDROCK]),
        BackendKind.DEEPSEEK: OpenAICompatibleBackend(config.backends[BackendKind.DEEPSEEK]),
        BackendKind.KIMI: OpenAICompatibleBackend(config.backends[BackendKind.KIMI]),
        BackendKind.CLAUDE_CODE_CLI: ClaudeCodeCliBackend(config.backends[BackendKind.CLAUDE_CODE_CLI]),
        BackendKind.CODEX_CLI: CodexCliBackend(config.backends[BackendKind.CODEX_CLI]),
    }


def build_manager(config: Config | None = None) -> Manager:
    resolved_config = config or Config()
    return Manager(
        clipboard=ClipboardManager(),
        prompt_builder=PromptBuilder(),
        sanitizer=InputSanitizer(),
        trust_wrapper=TrustWrapper(),
        nonce_service=NonceService(),
        backends=build_backends(resolved_config),
        default_backend=resolved_config.default_backend,
        transformers=CLIPBOARD_OPERATIONS,
    )
