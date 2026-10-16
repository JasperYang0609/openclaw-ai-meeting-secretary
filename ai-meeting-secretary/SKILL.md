---
name: ai-meeting-secretary
description: "Transcribe meetings, preserve a local record, update approved Notion sections, extract traceable tasks, require human confirmation, and optionally publish confirmed knowledge to Gemini RAG."
license: MIT
homepage: "https://github.com/JasperYang0609/openclaw-ai-meeting-secretary"
---

# AI Meeting Secretary

Turn meeting recordings into traceable records and confirmed action items. Use the smallest configured workflow and fail closed when setup, identity, source integrity, or approval is incomplete.

## Start with onboarding

Read [onboarding-config.example.json](assets/onboarding-config.example.json) and [notion-contract.md](references/notion-contract.md). Do not enter the live meeting flow until the organization has supplied and verified:

- organization name and at least one department;
- Notion transcript, meeting-record, task-master, and department database targets;
- a meeting template with a clear human/AI boundary;
- a Discord notification channel;
- a manual or scheduled downstream task-dispatch mode;
- optional RAG approval, canonical directory, source identity, and access design.

Validate the private onboarding file:

```bash
python3 <skill-root>/scripts/validate_onboarding_config.py /path/to/onboarding.json
```

If RAG is enabled, read [meeting-rag-contract.md](references/meeting-rag-contract.md). Only `google-gemini` / `gemini-embedding-001` is supported for production indexing. Never fall back to another embedding provider.

## Process one meeting

### 1. Verify inputs

Require:

- a recording link or local recording supplied by the organizer;
- a new meeting page copied from the approved template, or an approved project hub in which a child meeting page may be created;
- the organizer-completed human section.

If the user supplies the template itself, stop and ask for a copied meeting page. Never write into the template.

### 2. Transcribe and preserve locally

Use the configured speech-to-text tool. Preserve meeting order and do not invent missing audio.

Before mirroring to Notion, save a complete cleaned Markdown transcript under a customer-separated path:

```text
records/meeting-notes/<counterparty>/<project>/YYYY-MM-DD-<meeting>/transcript-clean.md
```

For internal meetings, use `internal/<project>/...`; use `general` when no stable project exists. Long transcripts may be split into ordered parts only when the directory contains an index and the combined content is complete.

Validate the saved transcript:

```bash
python3 <skill-root>/scripts/validate_local_transcript.py /path/to/transcript-clean.md
```

If the file is missing, empty, unreadable, truncated, or inconsistent with the recording range, stop with `BLOCKED_LOCAL_TRANSCRIPT`. Cloud copies never replace this local completion gate.

### 3. Respect the Notion boundary

Read the human section for context but never edit or delete it. Write only below the approved AI marker.

In the AI section, add:

- meeting summary and discussion topics;
- decisions and unresolved questions;
- next-meeting goals;
- action items with department, owner, deadline, source topic, and transcript evidence.

If an owner, department, deadline, or decision is ambiguous, mark it `Needs confirmation`; do not guess.

If the supplied page is a project hub rather than a formal meeting page, create one child page named `YYYY-MM-DD | Counterparty | Topic`. Keep the full record and transcript in the child page; leave only the page link in the hub.

### 4. Create traceable tasks

Create the meeting-specific task database inside the meeting page. Every task needs:

- task name and description;
- department and owner;
- deadline and status;
- source meeting and source topic;
- transcript excerpt or other direct evidence;
- human-confirmed flag and confirmer;
- dispatched flag.

Do not dispatch tasks yet.

### 5. Require two-stage human confirmation

Notify the configured Discord channel with the meeting page and task count. Ask a human to verify the meeting record and task details in Notion.

Proceed only when:

1. Discord receives the configured confirmation phrase; and
2. Notion shows both the meeting record and task rows as confirmed with a named confirmer.

If either check is missing, stop and remind the user. Unconfirmed records must not be dispatched or indexed.

### 6. Publish confirmed knowledge when approved

When RAG is enabled and approved:

1. Create or update the stable `summary.md` for the meeting.
2. Include a cleaned transcript only when the customer explicitly approved that source scope.
3. Validate the Markdown with `validate_meeting_record.py`.
4. Run the existing Gemini RAG incremental index.
5. Read back provider, model, source, and changed-file evidence.
6. Run the coverage audit and one source-grounded natural-language recall test.

Only then mark the meeting `RAG_READY`. Otherwise preserve the confirmed record and use `RAG_PENDING` or `RAG_ERROR` without changing providers.

### 7. Dispatch confirmed tasks

Sync only confirmed tasks to the configured task-master database. Preserve meeting, topic, and transcript evidence. Trigger the downstream department workflow once; do not overwrite later department status or redispatch an already-sent task.

## Never do these

- Write into the master template or human-authored section.
- Claim transcription is complete without a verified local Markdown transcript.
- Infer a speaker, owner, department, deadline, or approval that was not confirmed.
- Dispatch or index unconfirmed content.
- Store different customers in the same unprotected directory or retrieval route.
- Treat a project label, prompt, or Markdown field as authorization.
- Commit recordings, transcripts, completed onboarding files, IDs, secrets, or customer data.
- Use Qwen or any other fallback embedding provider.

