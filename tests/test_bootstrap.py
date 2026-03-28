from multipass.application.backends import BackendKind
from multipass.bootstrap import build_backends, build_manager
from multipass.infrastructure.config import Config


def test_build_backends_returns_all_configured_backends() -> None:
    config = Config()

    backends = build_backends(config)

    assert set(backends) == set(config.backends)


def test_build_manager_uses_configured_default_backend() -> None:
    config = Config(default_backend=BackendKind.KIMI)

    manager = build_manager(config)

    assert manager._default_backend is BackendKind.KIMI
