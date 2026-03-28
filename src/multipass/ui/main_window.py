from dataclasses import dataclass, field

from multipass.ui.chat_window import ChatWindow


@dataclass
class MainWindow:
    title: str = "multipass"
    windows: dict[str, ChatWindow] = field(default_factory=dict)

    def open_chat(self, window_id: str, chat_window: ChatWindow | None = None) -> ChatWindow:
        window = chat_window or ChatWindow(id=window_id)
        self.windows[window_id] = window
        return window
