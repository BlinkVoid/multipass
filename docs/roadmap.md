# Roadmap

This document tracks the most important next steps for Multipass as a product, not just as a codebase.

## Near Term

### Clipboard Core

- expand the non-AI clipboard toolkit
- group actions by category instead of one flat list
- add safer previews for destructive or lossy transforms
- support larger text artifacts without the UI feeling brittle

### Hosted APIs

- harden DeepSeek and Kimi as the primary in-app chat path
- improve provider configuration and error reporting
- make fallback to Bedrock explicit rather than implicit
- normalize streaming behavior across providers

### CLI Tools

- keep terminal-first launch as the default behavior for coding agents
- improve terminal session startup context
- pass workspace and intent cleanly to `claude` and `codex`
- revisit in-app terminal or API-backed agent bridging later, after the hosted path is stable

## UX Direction

The current UI is functional but not yet product-grade.

### Design Goals

- make clipboard work the primary surface, not a side feature
- make hosted chat and CLI launch modes visually distinct
- reduce layout ambiguity and dead space
- use stronger visual hierarchy, spacing, and typography

### Planned UI Changes

- grouped clipboard action sections
- more deliberate icons and button treatments
- clearer backend mode cards: `Hosted API` vs `CLI Tool`
- stronger conversation layout for streamed responses and activity events
- more polished theming rather than a generic control-panel look

## Medium Term

- richer clipboard operations for URLs, tables, encodings, and text cleanup
- saved presets for repeated workflows
- structured backend settings in the UI
- better session history inside the running app
- packaging/distribution for real desktop use

## Longer Term

- optional in-app terminal bridge for CLI tools if the UX and protocol are worth the complexity
- plugin-style operation system for community-contributed transforms
- stronger safety and auditability around model-facing prompt assembly
