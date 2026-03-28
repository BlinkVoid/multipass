# multipass

Initial scaffold for a layered clipboard/chat application with a dedicated prompt-security pipeline and pluggable hosted/CLI backends.

## Layout

- `src/multipass/ui`: UI entry points and presentation-facing placeholders
- `src/multipass/application`: orchestration layer
- `src/multipass/domain`: pure transformation logic and shared result types
- `src/multipass/security`: sanitization, trust boundaries, nonce generation, prompt building
- `src/multipass/infrastructure`: clipboard, logging, config, backend adapters, and worker abstractions
- `docs/architecture.md`: architecture and security notes
- `tests`: baseline tests for prompt-security behavior

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Smoke test a backend

Use the helper script to exercise a configured backend through the application manager:

```bash
uv run --project . python scripts/smoke_chat.py --backend deepseek --message "Hello"
```

Available backends:

- `deepseek`
- `kimi`
- `bedrock`
- `claude_code_cli`
- `codex_cli`

Optional flags:

- `--operation chat`
- `--window-id test-window`
- `--show-prompt`

## Run the Desktop App

Launch the Flet desktop UI from the repo root:

```bash
uv run --project . multipass-desktop
```

Or directly:

```bash
uv run --project . python -m multipass.ui
```

The current desktop shell includes:

- a more polished card-based layout
- staged and active backend selection
- one-click clipboard action buttons
- clipboard input/output preview panes
- chat transcript and activity feed
- prompt inspector for the last request
