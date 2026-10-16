# OpenClaw AI Meeting Secretary

A customer-neutral OpenClaw Skill and validator toolkit for turning meeting recordings into traceable meeting records and human-confirmed action items.

It is designed for teams that use Discord for workflow notifications and Notion for meeting collaboration. The Skill defines the required local transcript, approved AI section, confirmation receipt, and optional RAG gates that an OpenClaw agent must enforce with the organization's configured tools.

> This repository is an OpenClaw Skill package, not a hosted SaaS product. It does not include credentials, customer data, a speech-to-text engine, a Notion/Discord connector, a task dispatcher, or a Gemini RAG executor. The included validators check local artifacts and provider-readback receipts; they do not replace source-system authorization.

## What it includes

1. A customer-neutral setup contract for organization, department, Notion, Discord, local storage, and optional RAG identities.
2. A meeting workflow that tells an OpenClaw agent how to use the organization's configured tools.
3. Local validators for transcript artifact checks, onboarding structure, confirmation receipts, and RAG-eligible Markdown.
4. Templates for the Notion human/AI boundary, action-item traceability, and confirmed meeting summaries.
5. CI checks for negative paths, secrets, package contents, and deterministic archives.

## Safety boundaries

- The template itself is never used as a write target.
- Human-authored sections are read-only.
- Missing owners, departments, deadlines, or ambiguous statements are marked for confirmation instead of guessed.
- A local, readable transcript plus first/last recording markers and human completeness review are required before the transcription stage can be marked complete.
- Dispatch and indexing require fresh provider readback plus a valid confirmation receipt; this repository does not perform either external write.
- Raw audio, uncorrected transcripts, private chatter, secrets, and unapproved attachments are excluded from RAG.
- RAG project labels are metadata, not access control. Sensitive departments require an isolated or permission-aware retrieval route.
- Gemini is the only supported production embedding route in this package. There is no fallback provider.

## Repository layout

```text
ai-meeting-secretary/
├── SKILL.md
├── assets/
│   ├── confirmation-receipt.example.json
│   ├── meeting-record-template.md
│   ├── notion-meeting-template.md
│   └── onboarding-config.example.json
├── references/
│   ├── architecture.md
│   ├── meeting-rag-contract.md
│   └── notion-contract.md
└── scripts/
    ├── validate_confirmation_receipt.py
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

## Verify a local transcript artifact

```bash
python3 ai-meeting-secretary/scripts/validate_local_transcript.py \
  /path/to/records/meeting-notes/example/general/2026-01-15-kickoff/transcript-clean.md \
  --completion-gate \
  --expected-first-marker "00:00" \
  --expected-last-marker "12:33"
```

The completion gate verifies that both markers exist in the correct order. It cannot prove that every spoken sentence was transcribed correctly. A human must still compare the transcript with the recording or an independently generated source artifact before marking it complete.

## Verify the confirmation receipt

```bash
python3 ai-meeting-secretary/scripts/validate_confirmation_receipt.py \
  /path/to/provider-readback-receipt.json \
  --config /path/to/private/onboarding.json \
  --expected-meeting-id example-2026-01-15-kickoff \
  --expected-request-id request-unique-value
```

The receipt must be built from fresh Discord and Notion API readback in the same run. The validator does not fetch or authenticate provider data itself and must not be treated as an authorization system.

## Verify a confirmed meeting record

```bash
python3 ai-meeting-secretary/scripts/validate_meeting_record.py \
  /path/to/summary.md \
  --expected-customer-id example-organization \
  --expected-index-project ExampleOrganizationMeetings \
  --confirmation-receipt /path/to/provider-readback-receipt.json \
  --onboarding-config /path/to/private/onboarding.json \
  --expected-request-id request-unique-value
```

Passing this validator does not index anything. It only checks that the document and receipt identities are eligible for the configured Gemini RAG gate.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_public_release.py
python3 scripts/build_skill_archive.py --check
```

## Optional Gemini RAG integration

The meeting Skill does not create a second vector database or execute indexing. It defines how an OpenClaw agent may integrate with an existing, customer-isolated Gemini RAG installation. Before enabling it, record explicit approval for the exact source scope and verify:

- provider: `google-gemini`
- model: `gemini-embedding-001`
- stable customer ID and source ID
- isolated canonical directory and retrieval route
- incremental indexing receipt, coverage audit, and natural-language recall result

See [meeting-rag-contract.md](ai-meeting-secretary/references/meeting-rag-contract.md).

## Maintainer use of AI

AI-assisted maintenance may be used for public documentation, tests, and reusable workflow improvements. Do not use customer recordings, transcripts, meeting pages, task records, credentials, or private organization data as repository fixtures or review inputs.
