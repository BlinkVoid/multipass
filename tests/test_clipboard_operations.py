from multipass.application.clipboard_operations import CLIPBOARD_OPERATIONS
from multipass.bootstrap import build_manager
from multipass.domain.result import Ok
from multipass.infrastructure.config import Config


def test_bootstrap_manager_registers_clipboard_operations() -> None:
    manager = build_manager(Config())

    manager._clipboard.write_text("a   b")
    result = manager.run_clipboard_operation("normalize_whitespace")

    assert isinstance(result, Ok)
    assert result.value == "a b"
    assert manager._clipboard.read_text() == "a b"


def test_execute_clipboard_operation_sets_source_and_returns_transformed_result() -> None:
    manager = build_manager(Config())

    result = manager.execute_clipboard_operation("encode_base64", "hello")

    assert isinstance(result, Ok)
    assert result.value == "aGVsbG8="
    assert manager.read_clipboard() == "aGVsbG8="


def test_clipboard_operation_registry_contains_encoding_and_url_utilities() -> None:
    assert {"encode_base64", "decode_base64", "url_encode", "url_decode", "extract_hostname"} <= set(
        CLIPBOARD_OPERATIONS
    )
