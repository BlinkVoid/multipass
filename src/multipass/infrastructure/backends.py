from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import pty
import select
import subprocess
from typing import Callable, Iterable
from urllib import error, request
from uuid import uuid4

import boto3

from multipass.application.backends import (
    BackendCapabilities,
    BackendConfig,
    BackendKind,
    ChatBackend,
    SessionHandle,
)
from multipass.domain.chat import ApprovalRequest, ChatMessage, StreamEvent, StreamEventType
from multipass.security.prompt_builder import PreparedPrompt


@dataclass(frozen=True)
class CliInvocation:
    executable: str
    args: tuple[str, ...]
    input_text: str
    env: dict[str, str] = field(default_factory=dict)


class OpenAICompatibleFormatter:
    def format(self, model: str, prompt: PreparedPrompt, history: list[ChatMessage]) -> dict[str, object]:
        messages = [{"role": "system", "content": prompt.system_prompt}]
        for message in history:
            messages.append({"role": message.role.value, "content": message.content})
        messages.append({"role": "user", "content": prompt.user_prompt})
        return {"model": model, "messages": messages, "stream": True}


class BedrockFormatter:
    def format(self, model: str, prompt: PreparedPrompt, history: list[ChatMessage]) -> dict[str, object]:
        messages = []
        for message in history:
            messages.append({"role": message.role.value, "content": [{"text": message.content}]})
        messages.append({"role": "user", "content": [{"text": prompt.user_prompt}]})
        return {
            "modelId": model,
            "system": [{"text": prompt.system_prompt}],
            "messages": messages,
        }


class OpenAICompatibleBackend(ChatBackend):
    def __init__(
        self,
        config: BackendConfig,
        transport: Callable[[dict[str, object]], Iterable[StreamEvent]] | None = None,
    ) -> None:
        super().__init__(config)
        self._formatter = OpenAICompatibleFormatter()
        self._transport = transport or self._default_transport
        self.last_request: dict[str, object] | None = None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            streaming=True,
            approvals=False,
            file_actions=False,
            session_reuse=True,
            structured_output=True,
        )

    def start_session(self) -> SessionHandle:
        return SessionHandle(id=str(uuid4()), backend_kind=self.config.kind, model=self.config.model)

    def stream(
        self,
        session: SessionHandle,
        prompt: PreparedPrompt,
        history: list[ChatMessage],
    ) -> Iterable[StreamEvent]:
        _ = session
        payload = self._formatter.format(self.config.model, prompt, history)
        self.last_request = payload
        yield from self._transport(payload)

    def _default_transport(self, payload: dict[str, object]) -> Iterable[StreamEvent]:
        if not self.config.endpoint or not self.config.api_key_env:
            yield StreamEvent(type=StreamEventType.ERROR, text="OpenAI-compatible backend is missing endpoint configuration.")
            return

        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            yield StreamEvent(type=StreamEventType.ERROR, text=f"Missing API key env var: {self.config.api_key_env}")
            return

        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=f"{self.config.endpoint.rstrip('/')}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request) as response:
                yield StreamEvent(type=StreamEventType.STATUS, text="stream_open")
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        yield StreamEvent(type=StreamEventType.COMPLETED, text="")
                        continue
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield StreamEvent(type=StreamEventType.TOKEN, text=token)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            yield StreamEvent(type=StreamEventType.ERROR, text=f"HTTP {exc.code}: {detail}")
        except error.URLError as exc:
            yield StreamEvent(type=StreamEventType.ERROR, text=f"Connection error: {exc.reason}")


class BedrockBackend(ChatBackend):
    def __init__(
        self,
        config: BackendConfig,
        transport: Callable[[dict[str, object]], Iterable[StreamEvent]] | None = None,
    ) -> None:
        super().__init__(config)
        self._formatter = BedrockFormatter()
        self._transport = transport or self._default_transport
        self.last_request: dict[str, object] | None = None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            streaming=True,
            approvals=False,
            file_actions=False,
            session_reuse=True,
            structured_output=False,
        )

    def start_session(self) -> SessionHandle:
        return SessionHandle(id=str(uuid4()), backend_kind=self.config.kind, model=self.config.model)

    def stream(
        self,
        session: SessionHandle,
        prompt: PreparedPrompt,
        history: list[ChatMessage],
    ) -> Iterable[StreamEvent]:
        _ = session
        payload = self._formatter.format(self.config.model, prompt, history)
        self.last_request = payload
        yield from self._transport(payload)

    def _default_transport(self, payload: dict[str, object]) -> Iterable[StreamEvent]:
        region_name = (
            self.config.metadata.get("aws_region")
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )
        client = boto3.client("bedrock-runtime", region_name=region_name)
        try:
            response = client.converse_stream(
                modelId=payload["modelId"],
                system=payload["system"],
                messages=payload["messages"],
            )
            yield StreamEvent(type=StreamEventType.STATUS, text="stream_open")
            for event in response.get("stream", []):
                content_delta = event.get("contentBlockDelta", {})
                delta = content_delta.get("delta", {})
                token = delta.get("text", "")
                if token:
                    yield StreamEvent(type=StreamEventType.TOKEN, text=token)
                    continue
                if event.get("messageStop"):
                    yield StreamEvent(type=StreamEventType.COMPLETED, text="")
        except Exception as exc:
            yield StreamEvent(type=StreamEventType.ERROR, text=f"Bedrock error: {exc}")


class CliAgentBackend(ChatBackend):
    def __init__(
        self,
        config: BackendConfig,
        runner: Callable[[CliInvocation], Iterable[StreamEvent]] | None = None,
    ) -> None:
        super().__init__(config)
        self._runner = runner or self._default_runner
        self.last_invocation: CliInvocation | None = None
        self.last_approval: tuple[ApprovalRequest, bool] | None = None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            streaming=True,
            approvals=True,
            file_actions=True,
            session_reuse=True,
            structured_output=True,
        )

    def start_session(self) -> SessionHandle:
        return SessionHandle(id=str(uuid4()), backend_kind=self.config.kind, model=self.config.model)

    def stream(
        self,
        session: SessionHandle,
        prompt: PreparedPrompt,
        history: list[ChatMessage],
    ) -> Iterable[StreamEvent]:
        _ = session
        invocation = self.build_invocation(prompt, history)
        self.last_invocation = invocation
        yield from self._runner(invocation)

    def approve(self, session: SessionHandle, approval: ApprovalRequest, decision: bool) -> Iterable[StreamEvent]:
        _ = session
        self.last_approval = (approval, decision)
        result = "approved" if decision else "rejected"
        return [
            StreamEvent(
                type=StreamEventType.STATUS,
                text=f"approval_{result}",
                metadata={"approval_id": approval.id},
            )
        ]

    def build_invocation(self, prompt: PreparedPrompt, history: list[ChatMessage]) -> CliInvocation:
        raise NotImplementedError

    def _default_runner(self, invocation: CliInvocation) -> Iterable[StreamEvent]:
        command = [invocation.executable, *invocation.args]
        env = os.environ.copy()
        env.update(invocation.env)
        master_fd, slave_fd = pty.openpty()
        try:
            process = subprocess.Popen(
                command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=self.config.workspace,
                env=env,
            )
        except FileNotFoundError:
            os.close(master_fd)
            os.close(slave_fd)
            yield StreamEvent(type=StreamEventType.ERROR, text=f"Executable not found: {invocation.executable}")
            return

        os.close(slave_fd)

        yield StreamEvent(
            type=StreamEventType.STATUS,
            text="process_started",
            metadata={"executable": invocation.executable, "args": " ".join(invocation.args)},
        )

        if invocation.input_text:
            os.write(master_fd, invocation.input_text.encode("utf-8", errors="replace"))
        os.write(master_fd, b"\n\x04")

        buffer = ""
        try:
            while True:
                ready, _, _ = select.select([master_fd], [], [], 0.1)
                if ready:
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        chunk = b""
                    if chunk:
                        buffer += chunk.decode("utf-8", errors="replace")
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            text = line.rstrip("\r")
                            if text:
                                yield StreamEvent(type=StreamEventType.TOKEN, text=text)
                if process.poll() is not None and not ready:
                    break
            if buffer.strip():
                yield StreamEvent(type=StreamEventType.TOKEN, text=buffer.strip())
        finally:
            os.close(master_fd)

        return_code = process.wait()
        if return_code == 0:
            yield StreamEvent(type=StreamEventType.COMPLETED, text="")
            return
        yield StreamEvent(type=StreamEventType.ERROR, text=f"Process exited with status {return_code}")


class ClaudeCodeCliBackend(CliAgentBackend):
    def build_invocation(self, prompt: PreparedPrompt, history: list[ChatMessage]) -> CliInvocation:
        del history
        executable = self.config.executable or "claude"
        base_args = ("-p", "--output-format", "stream-json", "--input-format", "stream-json")
        payload = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": self._compose_cli_prompt(prompt)}],
            },
        }
        return CliInvocation(
            executable=executable,
            args=base_args + self.config.args,
            input_text=json.dumps(payload),
        )

    def _compose_cli_prompt(self, prompt: PreparedPrompt) -> str:
        return f"{prompt.system_prompt}\n\n{prompt.user_prompt}"


class CodexCliBackend(CliAgentBackend):
    def build_invocation(self, prompt: PreparedPrompt, history: list[ChatMessage]) -> CliInvocation:
        del history
        executable = self.config.executable or "codex"
        args = self.config.args
        return CliInvocation(
            executable=executable,
            args=args,
            input_text=f"{prompt.system_prompt}\n\n{prompt.user_prompt}",
        )
