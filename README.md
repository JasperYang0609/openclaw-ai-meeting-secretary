# OpenClaw AI Meeting Secretary

A customer-neutral OpenClaw Skill for turning meeting recordings into traceable meeting records and human-confirmed action items.

It is designed for teams that use Discord for workflow notifications and Notion for meeting collaboration. The Skill keeps a complete local Markdown transcript, writes only inside an approved AI section, and blocks task dispatch until a human confirms both the meeting record and the extracted tasks.

> This repository is an OpenClaw Skill package, not a hosted SaaS product. It does not include credentials, customer data, a speech-to-text provider, or a preconfigured Notion workspace.

## What it does

1. Validates the organization, department, Notion, Discord, and optional RAG setup.
2. Accepts a recording link and a meeting page copied from an approved template.
3. Produces and verifies a complete local Markdown transcript before cloud mirroring.
4. Reads the human-authored section without editing it.
5. Writes the summary, decisions, unresolved items, and action items only in the designated AI section.
6. Requires human confirmation before task dispatch.
7. Optionally publishes confirmed meeting knowledge to an isolated Gemini RAG route using `gemini-embedding-001`.

## Safety boundaries

- The template itself is never used as a write target.
- Human-authored sections are read-only.
- Missing owners, departments, deadlines, or ambiguous statements are marked for confirmation instead of guessed.
- A local, readable transcript is required before the transcription stage can be marked complete.
- Unconfirmed meeting notes and tasks are not dispatched or indexed.
- Raw audio, uncorrected transcripts, private chatter, secrets, and unapproved attachments are excluded from RAG.
- RAG project labels are metadata, not access control. Sensitive departments require an isolated or permission-aware retrieval route.
- Gemini is the only supported production embedding route in this package. There is no fallback provider.

## Repository layout

```text
ai-meeting-secretary/
├── SKILL.md
├── assets/
│   ├── meeting-record-template.md
│   ├── notion-meeting-template.md
│   └── onboarding-config.example.json
├── references/
│   ├── architecture.md
│   ├── meeting-rag-contract.md
│   └── notion-contract.md
└── scripts/
    ├── validate_local_transcript.py
    ├── validate_meeting_record.py
    └── validate_onboarding_config.py
```

## Install

Install the Skill folder with a compatible Agent Skills installer:

```bash
npx skills add JasperYang0609/openclaw-ai-meeting-secretary@ai-meeting-secretary -g
```

Or clone the repository and copy `ai-meeting-secretary/` into your OpenClaw skills directory.

## Configure

Copy the example configuration outside the repository and replace every `REPLACE_WITH_*` value:

```bash
cp ai-meeting-secretary/assets/onboarding-config.example.json /path/to/private/onboarding.json
python3 ai-meeting-secretary/scripts/validate_onboarding_config.py /path/to/private/onboarding.json
```

Do not commit the completed configuration if it contains internal database IDs, channel IDs, organization names, or private paths.

## Verify a local transcript

```bash
python3 ai-meeting-secretary/scripts/validate_local_transcript.py \
  /path/to/records/meeting-notes/example/general/2026-01-15-kickoff/transcript-clean.md
```

Optional first and last markers can prove that the saved file covers the expected recording range:

```bash
python3 ai-meeting-secretary/scripts/validate_local_transcript.py \
  /path/to/transcript-clean.md \
  --expected-first-marker "00:00" \
  --expected-last-marker "12:33"
```

## Verify a confirmed meeting record

```bash
python3 ai-meeting-secretary/scripts/validate_meeting_record.py \
  /path/to/summary.md \
  --expected-customer-id example-organization \
  --expected-index-project ExampleOrganizationMeetings
```

Passing this validator does not index anything. It only checks that the document is eligible for the configured Gemini RAG gate.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_public_release.py
python3 scripts/build_skill_archive.py --check
```

## Optional Gemini RAG integration

The meeting Skill does not create a second vector database. It integrates with an existing, customer-isolated Gemini RAG installation. Before enabling it, record explicit approval for the exact source scope and verify:

- provider: `google-gemini`
- model: `gemini-embedding-001`
- stable customer ID and source ID
- isolated canonical directory and retrieval route
- incremental indexing receipt, coverage audit, and natural-language recall result

See [meeting-rag-contract.md](ai-meeting-secretary/references/meeting-rag-contract.md).

## Maintainer use of AI

AI-assisted maintenance may be used for public documentation, tests, and reusable workflow improvements. Do not use customer recordings, transcripts, meeting pages, task records, credentials, or private organization data as repository fixtures or review inputs.

