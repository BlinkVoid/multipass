# Multipass

Multipass is a desktop-first clipboard and chat workspace for switching between hosted LLM APIs and local coding CLIs.

Current focus:

- one-click clipboard transformations
- prompt-security boundaries for model-facing input
- pluggable backends for hosted APIs and local CLI tools
- a desktop UI for clipboard workflows and model interaction

## Current Status

This project is early-stage but usable.

What works today:

- hosted API backends inside the app UI:
  - `deepseek`
  - `kimi`
  - `bedrock`
- CLI backends launched in a real terminal window:
  - `claude_code_cli`
  - `codex_cli`
- one-click clipboard actions:
  - normalize whitespace
  - extract hostname
  - decode base64
  - encode base64
  - URL decode
  - URL encode

## Why It Exists

Multipass is built around one rule:

> model clients should not receive raw user-controlled text directly

Clipboard text and freeform input are treated as untrusted, sanitized, explicitly wrapped, and only then passed into prompt construction. The repo architecture separates:

- `domain`: pure transforms and result types
- `security`: sanitization, trust boundaries, nonce generation, prompt building
- `application`: orchestration and backend routing
- `infrastructure`: API clients, CLI launchers, config, clipboard adapters
- `ui`: desktop application layer

See [docs/architecture.md](/home/r345/workspace/multipass/docs/architecture.md) for the design notes.

## Setup

Recommended:

```bash
cd /home/r345/workspace/multipass
uv sync --extra dev
uv run --project . python -m pytest
```

## Run The Desktop App

```bash
cd /home/r345/workspace/multipass
uv run --project . multipass-desktop
```

You can also run:

```bash
uv run --project . python -m multipass.ui
```

## Backend Modes

Hosted API backends stay inside the app chat UI:

- `deepseek`
- `kimi`
- `bedrock`

CLI backends do not pretend to be embedded chat sessions. They open a normal terminal window instead:

- `claude_code_cli`
- `codex_cli`

That split is intentional. Hosted APIs fit the in-app chat model; terminal-first coding agents work better in a real terminal session for now.

## Smoke Test A Backend

```bash
uv run --project . python scripts/smoke_chat.py --backend deepseek --message "Hello"
```

Available backends:

- `deepseek`
- `kimi`
- `bedrock`
- `claude_code_cli`
- `codex_cli`

Useful flags:

- `--operation chat`
- `--window-id test-window`
- `--show-prompt`

## Environment

Hosted API backends require credentials in the environment:

- `DEEPSEEK_API_KEY`
- `MOONSHOT_API_KEY`
- AWS credentials for Bedrock, such as `AWS_PROFILE` and `AWS_REGION`

CLI backends require the corresponding executables to be installed and on `PATH`:

- `claude`
- `codex`

## Tests

Run the full suite with:

```bash
uv run --project . python -m pytest
```

## License

[MIT](/home/r345/workspace/multipass/LICENSE)
