# Security Policy

## Supported Scope

Multipass handles clipboard data, prompt construction, and model/provider integration. Security issues in these areas are in scope:

- prompt injection boundary failures
- trust-boundary violations
- sanitization bypasses
- accidental exposure of sensitive clipboard data
- backend credential handling flaws
- terminal launcher command-injection risks

## Reporting A Vulnerability

Do not open public GitHub issues for security reports.

Report vulnerabilities privately to the project maintainer through GitHub security reporting if available on the repository. If private reporting is not enabled yet, contact the maintainer directly before disclosing details publicly.

When reporting, include:

- affected version or commit
- reproduction steps
- security impact
- any proof-of-concept inputs

## Security Expectations For Contributors

- Do not bypass the `InputSanitizer` -> `TrustWrapper` -> `PromptBuilder` flow for model-facing input.
- Treat clipboard and freeform user text as untrusted by default.
- Keep trusted prompt sections code-generated.
- Avoid introducing shell execution paths that interpolate raw user-controlled strings without validation.

## Disclosure

Please allow reasonable time for triage and remediation before public disclosure.
