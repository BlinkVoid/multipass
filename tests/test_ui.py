from multipass.application.backends import BackendKind
from multipass.domain.chat import ApprovalRequest, StreamEvent, StreamEventType
from multipass.domain.result import Ok
from multipass.infrastructure.clipboard_manager import ClipboardManager
from multipass.infrastructure.config import Config
from multipass.security.nonce_service import NonceBundle
from multipass.security.prompt_builder import PromptBuilder, TrustWrapper
from multipass.ui.chat_window import ChatWindow, WindowStatus
from multipass.ui.desktop_app import DesktopController, MultipassApp


class DummyManager:
    def __init__(self) -> None:
        self._clipboard = ClipboardManager()
        self.set_backend_calls: list[BackendKind] = []
        self.stream_calls: list[BackendKind] = []

    def set_backend(self, window_id: str, backend_kind: BackendKind) -> None:
        _ = window_id
        self.set_backend_calls.append(backend_kind)

    def available_clipboard_operations(self) -> tuple[str, ...]:
        return ("normalize_whitespace",)

    def read_clipboard(self) -> str:
        return self._clipboard.read_text()

    def execute_clipboard_operation(self, operation: str, source_text: str):
        if operation != "normalize_whitespace":
            raise KeyError(operation)
        normalized = " ".join(source_text.split())
        self._clipboard.write_text(normalized)
        return Ok(normalized)

    def send_ai_request(self, operation: str, raw_input: str, window_id: str, backend_kind: BackendKind):
        _ = operation
        _ = raw_input
        _ = window_id
        self.stream_calls.append(backend_kind)
        builder = PromptBuilder()
        prompt = builder.build(
            operation="chat",
            wrapped_input=TrustWrapper().wrap("hello"),
            nonce=NonceBundle(request_nonce="nonce", time_marker="2026-03-28T00:00:00+00:00"),
        )
        return prompt, [
            StreamEvent(type=StreamEventType.TOKEN, text=backend_kind.value),
            StreamEvent(type=StreamEventType.COMPLETED, text=""),
        ]


class DummyWindow:
    def __init__(self) -> None:
        self.width = 0
        self.height = 0


class DummyPage:
    def __init__(self) -> None:
        self.title = ""
        self.theme_mode = None
        self.bgcolor = ""
        self.window = DummyWindow()
        self.padding = 0
        self.spacing = 0
        self.fonts = {}
        self.theme = None
        self.dialog = None
        self.controls: list[object] = []
        self.clipboard_value = ""
        self.opened_control = None

    def add(self, *controls: object) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        return None

    def get_clipboard(self) -> str:
        return self.clipboard_value

    def set_clipboard(self, data: str) -> None:
        self.clipboard_value = data

    def open(self, control: object) -> None:
        self.opened_control = control

    def close(self, control: object) -> None:
        if self.opened_control is control:
            self.opened_control = None


def _collect_text_values(control: object) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(getattr(control, "value"), str):
        values.append(getattr(control, "value"))
    if hasattr(control, "text") and isinstance(getattr(control, "text"), str):
        values.append(getattr(control, "text"))
    if hasattr(control, "hint_text") and isinstance(getattr(control, "hint_text"), str):
        values.append(getattr(control, "hint_text"))
    if hasattr(control, "content"):
        content = getattr(control, "content")
        if content is not None:
            values.extend(_collect_text_values(content))
    if hasattr(control, "controls"):
        for child in getattr(control, "controls"):
            values.extend(_collect_text_values(child))
    if hasattr(control, "title") and getattr(control, "title") is not None:
        values.extend(_collect_text_values(getattr(control, "title")))
    return values


def _walk_controls(control: object):
    children = getattr(control, "controls", None)
    if children is not None:
        for child in children:
            yield child
            yield from _walk_controls(child)
    content = getattr(control, "content", None)
    if content is not None:
        yield content
        yield from _walk_controls(content)


def _find_first(control: object, predicate):
    if predicate(control):
        return control
    for child in _walk_controls(control):
        if predicate(child):
            return child
    return None


def test_chat_window_tracks_streaming_and_approvals() -> None:
    window = ChatWindow(backend_kind=BackendKind.CLAUDE_CODE_CLI)

    window.apply_event(StreamEvent(type=StreamEventType.TOKEN, text="hello"))
    window.apply_event(
        StreamEvent(
            type=StreamEventType.APPROVAL_REQUIRED,
            approval=ApprovalRequest(id="1", kind="shell", summary="Run ls"),
        )
    )
    window.apply_event(StreamEvent(type=StreamEventType.STATUS, text="approval_approved"))
    window.apply_event(StreamEvent(type=StreamEventType.COMPLETED, text="done"))

    assert window.transcript[0] == "hello"
    assert window.status is WindowStatus.FINISHED
    assert window.pending_approvals == []
    assert "Run ls" in window.activity_feed


def test_desktop_controller_stages_and_activates_backend() -> None:
    manager = DummyManager()
    controller = DesktopController(manager=manager, config=Config())

    staged = controller.stage_backend(BackendKind.KIMI.value)
    active = controller.activate_backend()

    assert staged is BackendKind.KIMI
    assert active is BackendKind.KIMI
    assert manager.set_backend_calls[-1] is BackendKind.KIMI


def test_desktop_controller_runs_clipboard_action_and_chat() -> None:
    manager = DummyManager()
    controller = DesktopController(manager=manager, config=Config(default_backend=BackendKind.DEEPSEEK))

    clipboard_result = controller.run_clipboard_action("normalize_whitespace", "a   b")
    prompt, events = controller.send_chat("hello")

    assert clipboard_result == "a b"
    assert manager.read_clipboard() == "a b"
    assert prompt.operation == "chat"
    assert events[0].text == BackendKind.DEEPSEEK.value


def test_desktop_controller_launches_terminal_for_cli_backend() -> None:
    launched: list[list[str]] = []
    manager = DummyManager()
    controller = DesktopController(
        manager=manager,
        config=Config(default_backend=BackendKind.CLAUDE_CODE_CLI),
        terminal_opener=lambda command: launched.append(command),
    )

    command = controller.launch_cli_terminal("check repo")

    assert launched and launched[0] == command
    assert "gnome-terminal" in command[0] or "x-terminal-emulator" in command[0]
    assert "claude" in " ".join(command)


def test_flet_app_builds_without_dropdown_event_error() -> None:
    manager = DummyManager()
    controller = DesktopController(manager=manager, config=Config(default_backend=BackendKind.DEEPSEEK))
    page = DummyPage()

    app = MultipassApp(page=page, controller=controller)
    app.build()

    assert page.controls
    assert app.backend_picker.value == BackendKind.DEEPSEEK.value
    visible_text = _collect_text_values(page.controls[0])
    assert "Chat With Deepseek" in visible_text
    assert "Type your message to the active backend here." in visible_text
    assert app.active_text.value == BackendKind.DEEPSEEK.value
    assert app.message_input.hint_text == "Type your message to the active backend here."
    assert _find_first(page, lambda c: getattr(c, "text", None) == "Send" or getattr(c, "content", None) == "Send") is not None


def test_flet_app_switches_to_terminal_mode_for_cli_backend() -> None:
    manager = DummyManager()
    controller = DesktopController(manager=manager, config=Config(default_backend=BackendKind.DEEPSEEK))
    page = DummyPage()

    app = MultipassApp(page=page, controller=controller)
    app.build()
    controller.stage_backend(BackendKind.CLAUDE_CODE_CLI.value)
    controller.activate_backend()
    app._refresh_backend_labels()

    assert "Terminal Session" in app.chat_heading.value
    assert app.send_button.content == "Open Terminal"
    assert "terminal window" in app.chat_hint.value
