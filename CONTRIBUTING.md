# Contributing

Thanks for contributing to Multipass.

## Before You Start

- Read [README.md](/home/r345/workspace/multipass/README.md) for setup and current product scope.
- Read [docs/architecture.md](/home/r345/workspace/multipass/docs/architecture.md) before changing backend, security, or prompt code.
- Keep the core rule intact: model clients must not receive raw user-controlled text directly.

## Local Setup

```bash
cd /home/r345/workspace/multipass
uv sync --extra dev
uv run --project . python -m pytest
```

Run the desktop app with:

```bash
uv run --project . multipass-desktop
```

## Contribution Priorities

Current high-value areas:

- clipboard transformation coverage and UX
- hosted API backend reliability
- CLI launcher ergonomics
- prompt-security hardening
- desktop UI polish
- tests for regressions and backend contracts

## Development Rules

- Use `uv` for dependency and command execution.
- Keep domain transforms pure where possible.
- Route model-facing input through the security pipeline.
- Avoid provider-specific logic leaking into the UI layer.
- Prefer small, test-backed changes.

## Bug Fixes

If you fix a bug, first add or update a test that recreates the failing condition. Then fix the implementation and re-run the tests to prove the regression is covered.

## Pull Requests

Good pull requests usually include:

- a concise problem statement
- the design tradeoff if the change affects architecture
- tests for behavior changes
- screenshots for visible UI changes

## Style

- Prefer clear, direct code over clever abstractions.
- Keep comments sparse and useful.
- Preserve the trusted/untrusted separation in prompt-building code.

## Validation

Before opening a pull request, run:

```bash
python3 -m py_compile $(find src tests scripts -name '*.py' | sort)
uv run --project . python -m pytest
```
