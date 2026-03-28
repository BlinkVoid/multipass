from __future__ import annotations

from dataclasses import dataclass, field
import os
import shlex
import shutil
import subprocess
from typing import Callable

import flet as ft

from multipass.application.backends import BackendKind
from multipass.application.manager import Manager
from multipass.bootstrap import build_manager
from multipass.domain.chat import StreamEvent, StreamEventType
from multipass.infrastructure.config import Config
from multipass.security.prompt_builder import PreparedPrompt


@dataclass
class DesktopController:
    manager: Manager
    config: Config
    window_id: str = "main"
    terminal_opener: Callable[[list[str]], None] | None = None
    staged_backend: BackendKind = field(init=False)
    active_backend: BackendKind = field(init=False)
    last_prompt: PreparedPrompt | None = None

    def __post_init__(self) -> None:
        self.staged_backend = self.config.default_backend
        self.active_backend = self.config.default_backend
        self.manager.set_backend(self.window_id, self.active_backend)

    def available_operations(self) -> tuple[str, ...]:
        return self.manager.available_clipboard_operations()

    def stage_backend(self, backend_name: str) -> BackendKind:
        self.staged_backend = BackendKind(backend_name)
        return self.staged_backend

    def activate_backend(self) -> BackendKind:
        self.active_backend = self.staged_backend
        self.manager.set_backend(self.window_id, self.active_backend)
        return self.active_backend

    def active_backend_is_cli(self) -> bool:
        return self.active_backend in {BackendKind.CLAUDE_CODE_CLI, BackendKind.CODEX_CLI}

    def backend_model(self, backend_kind: BackendKind | None = None) -> str:
        kind = backend_kind or self.active_backend
        return self.config.backends[kind].model

    def run_clipboard_action(self, operation: str, clipboard_text: str) -> str:
        self.manager.execute_clipboard_operation(operation, clipboard_text)
        return self.manager.read_clipboard()

    def send_chat(self, message: str) -> tuple[PreparedPrompt, list[StreamEvent]]:
        prompt, events = self.manager.send_ai_request(
            operation="chat",
            raw_input=message,
            window_id=self.window_id,
            backend_kind=self.active_backend,
        )
        self.last_prompt = prompt
        return prompt, events

    def launch_cli_terminal(self, initial_message: str = "") -> list[str]:
        backend_config = self.config.backends[self.active_backend]
        executable = backend_config.executable or self.active_backend.value
        command = [executable, *backend_config.args]
        workdir = backend_config.workspace or os.getcwd()
        quoted_command = " ".join(shlex.quote(part) for part in command)
        banner = (
            f"printf '%s\\n' 'Launching {self.active_backend.value} in a normal terminal session.';"
            f"printf '%s\\n' 'Working directory: {workdir}';"
        )
        if initial_message.strip():
            banner += f"printf '%s\\n' 'Initial note: {initial_message.strip()}';"
        script = f"cd {shlex.quote(workdir)} && {banner} exec {quoted_command}"

        launch_command: list[str]
        if shutil.which("gnome-terminal"):
            launch_command = ["gnome-terminal", "--", "bash", "-lc", script]
        elif shutil.which("x-terminal-emulator"):
            launch_command = ["x-terminal-emulator", "-e", "bash", "-lc", script]
        else:
            raise RuntimeError("No supported terminal launcher found.")

        opener = self.terminal_opener or self._default_terminal_opener
        opener(launch_command)
        return launch_command

    def _default_terminal_opener(self, command: list[str]) -> None:
        subprocess.Popen(command)


class MultipassApp:
    def __init__(self, page: ft.Page, controller: DesktopController) -> None:
        self.page = page
        self.controller = controller

        self.transcript = ft.ListView(expand=True, spacing=12, auto_scroll=True)
        self.activity = ft.ListView(expand=True, spacing=8, auto_scroll=True)
        self.approval_status = ft.Text("No pending approvals.", color=ft.Colors.GREY_400, size=13)
        self.prompt_dialog = ft.AlertDialog(modal=False)
        self.chat_heading = ft.Text("Chat With Active Backend", size=22, weight=ft.FontWeight.W_700, color="#f5f8fc")
        self.chat_hint = ft.Text(
            "Activate a backend, type a message below, then press Send.",
            size=13,
            color="#8ea3bf",
        )
        self.message_input = ft.TextField(
            multiline=True,
            min_lines=3,
            max_lines=6,
            border_radius=18,
            filled=True,
            fill_color="#18212f",
            border_color="#243247",
            text_size=15,
            hint_text="Type your message to the active backend here.",
        )
        self.send_button = ft.Button("Send", on_click=self._send_message, style=self._primary_button_style())
        self.status_chip = ft.Container()
        self.model_text = ft.Text(size=13, color="#9db0ca")
        self.staged_text = ft.Text(weight=ft.FontWeight.W_600, color="#e7eef8")
        self.active_text = ft.Text(weight=ft.FontWeight.W_600, color="#e7eef8")
        self.clipboard_in = ft.TextField(
            read_only=True,
            multiline=True,
            min_lines=6,
            max_lines=8,
            border_radius=16,
            filled=True,
            fill_color="#121a25",
            border_color="#243247",
            text_size=14,
        )
        self.clipboard_out = ft.TextField(
            read_only=True,
            multiline=True,
            min_lines=6,
            max_lines=8,
            border_radius=16,
            filled=True,
            fill_color="#121a25",
            border_color="#243247",
            text_size=14,
        )

    def build(self) -> None:
        self.page.title = self.controller.config.application_name
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0b1118"
        self.page.window.width = 1480
        self.page.window.height = 920
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.padding = 0
        self.page.spacing = 0
        self.page.fonts = {"Space Grotesk": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700"}
        self.page.theme = ft.Theme(font_family="Space Grotesk")
        self.page.dialog = self.prompt_dialog

        backend_options = [
            ft.dropdown.Option(kind.value, text=kind.value.replace("_", " ").title()) for kind in BackendKind
        ]
        self.backend_picker = ft.Dropdown(
            options=backend_options,
            value=self.controller.staged_backend.value,
            filled=True,
            fill_color="#121a25",
            border_color="#243247",
            border_radius=16,
            color="#e7eef8",
            on_select=self._on_stage_backend,
        )

        header = ft.Container(
            padding=ft.Padding.symmetric(horizontal=28, vertical=22),
            gradient=ft.LinearGradient(colors=["#111a24", "#0b1118"]),
            border=ft.Border.only(bottom=ft.BorderSide(1, "#1d2a3b")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("Multipass", size=30, weight=ft.FontWeight.W_700, color="#f4f7fb"),
                            ft.Text(
                                "Clipboard actions on the left. Chat and backend orchestration on the right.",
                                size=14,
                                color="#8aa0bb",
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Button(
                                "Show Last Prompt",
                                on_click=self._show_prompt,
                                style=self._secondary_button_style(),
                            ),
                            ft.Button(
                                "Activate Backend",
                                on_click=self._activate_backend,
                                style=self._primary_button_style(),
                            ),
                        ],
                    ),
                ],
            ),
        )

        left_panel = self._build_left_workspace()
        right_panel = self._build_right_workspace()

        body = ft.Container(
            expand=True,
            padding=ft.Padding.all(22),
            content=ft.Row(
                expand=True,
                spacing=18,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(width=420, content=left_panel),
                    ft.Container(expand=True, content=right_panel),
                ],
            ),
        )

        self.page.add(ft.Column(expand=True, spacing=0, controls=[header, body]))
        self._refresh_backend_labels()
        self._set_status("Idle", "#1a2635")
        self.page.update()

    def _build_clipboard_panel(self) -> ft.Control:
        buttons: list[ft.Control] = []
        accent_cycle = ["#ff7a59", "#1fb6ff", "#0fd68b", "#f5b700", "#ff5d8f", "#8e7dff"]
        for index, operation in enumerate(self.controller.available_operations()):
            label = operation.replace("_", " ").title()
            buttons.append(
                ft.Container(
                    gradient=ft.LinearGradient(colors=[accent_cycle[index % len(accent_cycle)], "#141d28"]),
                    border_radius=20,
                    padding=1,
                    content=ft.Button(
                        label,
                        on_click=self._clipboard_handler(operation),
                        style=ft.ButtonStyle(
                            color="#f8fbff",
                            bgcolor="#111925",
                            shape=ft.RoundedRectangleBorder(radius=18),
                            padding=22,
                            text_style=ft.TextStyle(size=15, weight=ft.FontWeight.W_600),
                        ),
                    ),
                )
            )

        return self._card(
            title="Clipboard Actions",
            subtitle="One click reads the OS clipboard, transforms it, and writes the result back.",
            content=ft.Column(spacing=12, controls=buttons),
        )

    def _build_preview_panel(self) -> ft.Control:
        return ft.Column(
            spacing=18,
            controls=[
                self._card(
                    title="Clipboard In",
                    subtitle="Last clipboard content used for an action.",
                    content=self.clipboard_in,
                ),
                self._card(
                    title="Clipboard Out",
                    subtitle="Last transformed result written back to the clipboard.",
                    content=self.clipboard_out,
                ),
            ],
        )

    def _build_left_workspace(self) -> ft.Control:
        return ft.Column(
            spacing=18,
            controls=[
                self._build_clipboard_panel(),
                self._build_preview_panel(),
            ],
        )

    def _build_chat_panel(self) -> ft.Control:
        controls_card = self._card(
            title="Chat Workspace",
            subtitle="Choose a backend, activate it, then talk to the active model here.",
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(expand=1, content=self.backend_picker),
                            ft.Container(content=self.status_chip, width=140),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(spacing=4, controls=[ft.Text("Staged", color="#7f93af", size=12), self.staged_text]),
                            ft.Column(spacing=4, controls=[ft.Text("Active", color="#7f93af", size=12), self.active_text]),
                            ft.Column(spacing=4, controls=[ft.Text("Model", color="#7f93af", size=12), self.model_text]),
                        ],
                    ),
                    self.chat_heading,
                    self.chat_hint,
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Text("Active backend", size=12, color="#7f93af"),
                            ft.Container(
                                border_radius=999,
                                bgcolor="#162230",
                                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                                content=self.active_text,
                            ),
                            ft.Container(
                                border_radius=999,
                                bgcolor="#162230",
                                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                                content=self.model_text,
                            ),
                        ],
                    ),
                    self.message_input,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[self.send_button],
                    ),
                    ft.Divider(color="#223145"),
                    ft.Text("Approvals", size=12, color="#7f93af"),
                    self.approval_status,
                ],
            ),
        )

        transcript_card = self._card(
            title="Conversation",
            subtitle="Active backend chat transcript and message history.",
            content=ft.Container(
                expand=True,
                border_radius=18,
                bgcolor="#101722",
                padding=18,
                content=self.transcript,
            ),
            expand=True,
        )

        activity_card = self._card(
            title="Activity",
            subtitle="Operational log and backend events.",
            content=ft.Container(
                height=220,
                border_radius=18,
                bgcolor="#101722",
                padding=18,
                content=self.activity,
            ),
        )

        return ft.Column(expand=True, spacing=18, controls=[controls_card, transcript_card, activity_card])

    def _build_right_workspace(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=18,
            controls=[self._build_chat_panel()],
        )

    def _card(self, title: str, subtitle: str, content: ft.Control, expand: bool = False) -> ft.Control:
        return ft.Container(
            expand=expand,
            padding=24,
            border_radius=28,
            bgcolor="#0f1621",
            border=ft.Border.all(1, "#1e2b3d"),
            shadow=ft.BoxShadow(blur_radius=40, color="#05080d", spread_radius=1, offset=ft.Offset(0, 14)),
            content=ft.Column(
                expand=expand,
                spacing=14,
                controls=[
                    ft.Text(title, size=20, weight=ft.FontWeight.W_700, color="#f5f8fc"),
                    ft.Text(subtitle, size=13, color="#8ea3bf"),
                    content,
                ],
            ),
        )

    def _primary_button_style(self) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            bgcolor={"": "#ff7a59"},
            color={"": "#0b1118"},
            shape=ft.RoundedRectangleBorder(radius=18),
            padding=ft.Padding.symmetric(horizontal=24, vertical=18),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_700),
        )

    def _secondary_button_style(self) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            bgcolor={"": "#141d28"},
            color={"": "#f5f8fc"},
            shape=ft.RoundedRectangleBorder(radius=18),
            padding=ft.Padding.symmetric(horizontal=20, vertical=18),
            side={"": ft.BorderSide(1, "#27374d")},
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        )

    def _refresh_backend_labels(self) -> None:
        self.staged_text.value = self.controller.staged_backend.value
        self.active_text.value = self.controller.active_backend.value
        self.model_text.value = self.controller.backend_model()
        if self.controller.active_backend_is_cli():
            self.chat_heading.value = f"Terminal Session For {self.controller.active_backend.value.replace('_', ' ').title()}"
            self.chat_hint.value = "This backend runs in a real terminal window. Use the button below to open it."
            self.message_input.hint_text = "Optional note to show when the terminal session starts."
            self.send_button.content = "Open Terminal"
        else:
            self.chat_heading.value = f"Chat With {self.controller.active_backend.value.replace('_', ' ').title()}"
            self.chat_hint.value = "Activate a backend, type a message below, then press Send."
            self.message_input.hint_text = "Type your message to the active backend here."
            self.send_button.content = "Send"

    def _set_status(self, text: str, color: str) -> None:
        self.status_chip.content = ft.Container(
            alignment=ft.Alignment(0, 0),
            border_radius=999,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=color,
            content=ft.Text(text, color="#f5f8fc", weight=ft.FontWeight.W_600, size=12),
        )

    def _append_activity(self, text: str) -> None:
        self.activity.controls.append(ft.Text(text, size=12, color="#9db0ca"))

    def _append_transcript(self, author: str, body: str, tone: str) -> None:
        bubble = ft.Container(
            padding=18,
            border_radius=22,
            bgcolor=tone,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text(author, size=12, color="#90a5c2", weight=ft.FontWeight.W_700),
                    ft.Text(body, size=14, color="#f4f7fb", selectable=True),
                ],
            ),
        )
        self.transcript.controls.append(bubble)

    def _on_stage_backend(self, e: ft.ControlEvent) -> None:
        if not e.control.value:
            return
        backend = self.controller.stage_backend(e.control.value)
        self.staged_text.value = backend.value
        self._append_activity(f"backend_staged: {backend.value}")
        self.page.update()

    def _activate_backend(self, e: ft.ControlEvent) -> None:
        del e
        backend = self.controller.activate_backend()
        self._refresh_backend_labels()
        self._append_activity(f"backend_loaded: {backend.value}")
        self.page.update()

    def _clipboard_handler(self, operation: str):
        async def handler(e: ft.ControlEvent) -> None:
            del e
            clipboard_text = await ft.Clipboard().get() or ""
            output = self.controller.run_clipboard_action(operation, clipboard_text)
            self.clipboard_in.value = clipboard_text
            self.clipboard_out.value = output
            await ft.Clipboard().set(output)
            self._append_activity(f"clipboard_operation: {operation}")
            self.page.update()

        return handler

    def _send_message(self, e: ft.ControlEvent) -> None:
        del e
        message = self.message_input.value.strip()
        if self.controller.active_backend_is_cli():
            self.message_input.value = ""
            command = self.controller.launch_cli_terminal(message)
            self._append_activity(f"terminal_opened: {' '.join(command[:3])}")
            self._append_transcript(
                "System",
                f"Opened a terminal session for {self.controller.active_backend.value}. Continue interacting in that terminal window.",
                "#18212f",
            )
            self._set_status("Terminal Opened", "#4a2d12")
            self.page.update()
            return

        if not message:
            return

        self.message_input.value = ""
        self._append_transcript(f"You [{self.controller.active_backend.value}]", message, "#18212f")
        self._set_status("Sending", "#1f3f5b")
        self.page.update()
        prompt, events = self.controller.send_chat(message)
        assistant_text = "".join(event.text for event in events if event.type is StreamEventType.TOKEN)
        activity_lines = [event.text or event.type.value for event in events]
        self.controller.last_prompt = prompt
        if assistant_text:
            self._append_transcript("Assistant", assistant_text, "#141d28")
        for line in activity_lines:
            self._append_activity(line)
        self._set_status("Ready", "#153622")
        self.page.update()

    def _show_prompt(self, e: ft.ControlEvent) -> None:
        del e
        if self.controller.last_prompt is None:
            self.page.open(ft.SnackBar(content=ft.Text("No prompt has been sent yet.")))
            self.page.update()
            return
        self.prompt_dialog.title = ft.Text("Last Prompt")
        self.prompt_dialog.content = ft.Container(
            width=760,
            content=ft.Text(
                f"{self.controller.last_prompt.system_prompt}\n\n---\n\n{self.controller.last_prompt.user_prompt}",
                selectable=True,
            ),
        )
        self.prompt_dialog.actions = [ft.TextButton("Close", on_click=lambda e: self.page.close(self.prompt_dialog))]
        self.page.open(self.prompt_dialog)
        self.page.update()


def main(page: ft.Page) -> None:
    controller = DesktopController(manager=build_manager(), config=Config())
    MultipassApp(page, controller).build()


def launch() -> None:
    ft.app(main)
