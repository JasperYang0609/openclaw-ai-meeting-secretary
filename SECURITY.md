# Security policy

## Reporting a vulnerability

Please use GitHub private vulnerability reporting for this repository. Do not open a public issue containing credentials, customer identifiers, transcript excerpts, internal URLs, or access-control details.

## Data handling expectations

- Keep recordings, transcripts, completed onboarding files, Notion IDs, Discord IDs, and private paths outside Git.
- Use synthetic fixtures in tests and documentation.
- Treat recordings, transcripts, meeting pages, and model output as untrusted input.
- Require a human confirmation gate before dispatching tasks or publishing meeting knowledge.
- Enforce source-system permissions independently. This Skill can narrow a workflow but cannot expand or replace Notion, Drive, database, or retrieval authorization.
- Use customer-isolated storage and retrieval routes when meeting data is sensitive.
- Do not send raw audio, secrets, uncorrected transcripts, or private chatter to an embedding provider.

## Supported versions

Security fixes are applied to the latest release on `main`.

