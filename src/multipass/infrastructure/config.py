from dataclasses import dataclass, field

from multipass.application.backends import BackendConfig, BackendKind


@dataclass(frozen=True)
class Config:
    application_name: str = "multipass"
    aws_region: str = "us-east-1"
    backends: dict[BackendKind, BackendConfig] = field(
        default_factory=lambda: {
            BackendKind.BEDROCK: BackendConfig(
                kind=BackendKind.BEDROCK,
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                endpoint="bedrock",
                api_key_env="AWS_PROFILE",
                metadata={"aws_region": "us-east-1"},
            ),
            BackendKind.DEEPSEEK: BackendConfig(
                kind=BackendKind.DEEPSEEK,
                model="deepseek-chat",
                endpoint="https://api.deepseek.com",
                api_key_env="DEEPSEEK_API_KEY",
            ),
            BackendKind.KIMI: BackendConfig(
                kind=BackendKind.KIMI,
                model="kimi-k2",
                endpoint="https://api.moonshot.ai/v1",
                api_key_env="MOONSHOT_API_KEY",
            ),
            BackendKind.CLAUDE_CODE_CLI: BackendConfig(
                kind=BackendKind.CLAUDE_CODE_CLI,
                model="claude-code",
                executable="claude",
            ),
            BackendKind.CODEX_CLI: BackendConfig(
                kind=BackendKind.CODEX_CLI,
                model="codex-cli",
                executable="codex",
            ),
        }
    )
    default_backend: BackendKind = BackendKind.DEEPSEEK
