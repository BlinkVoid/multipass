from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from multipass.application.backends import BackendKind
from multipass.bootstrap import build_manager
from multipass.domain.chat import StreamEventType
from multipass.infrastructure.config import Config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a smoke chat request against a configured backend.")
    parser.add_argument(
        "--backend",
        required=True,
        choices=[kind.value for kind in BackendKind],
        help="Backend to exercise.",
    )
    parser.add_argument("--message", required=True, help="User message to send.")
    parser.add_argument("--operation", default="chat", help="Operation label passed into the prompt builder.")
    parser.add_argument("--window-id", default="smoke", help="Conversation/window identifier.")
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the prepared system and user prompts before streaming events.",
    )
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    config = Config()
    backend_kind = BackendKind(args.backend)
    config.default_backend = backend_kind
    manager = build_manager(config)

    prompt, events = manager.send_ai_request(
        operation=args.operation,
        raw_input=args.message,
        window_id=args.window_id,
        backend_kind=backend_kind,
    )

    if args.show_prompt:
        print("=== SYSTEM PROMPT ===")
        print(prompt.system_prompt)
        print("=== USER PROMPT ===")
        print(prompt.user_prompt)

    print("=== EVENTS ===")
    for event in events:
        payload = {"type": event.type.value, "text": event.text, "metadata": event.metadata}
        if event.approval is not None:
            payload["approval"] = {
                "id": event.approval.id,
                "kind": event.approval.kind,
                "summary": event.approval.summary,
                "command": event.approval.command,
            }
        print(json.dumps(payload, ensure_ascii=True))

    assistant_text = "".join(event.text for event in events if event.type is StreamEventType.TOKEN)
    if assistant_text:
        print("=== ASSISTANT ===")
        print(assistant_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
