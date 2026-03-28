from multipass.security.sanitizer import InputSanitizer


def test_sanitizer_removes_unicode_tag_characters() -> None:
    sanitizer = InputSanitizer()

    raw = "alpha\U000E0001beta"
    result = sanitizer.sanitize(raw)

    assert result.text == "alphabeta"
    assert result.changed is True


def test_sanitizer_removes_surrogates() -> None:
    sanitizer = InputSanitizer()

    raw = "left\ud800right"
    result = sanitizer.sanitize(raw)

    assert result.text == "leftright"
    assert result.changed is True

