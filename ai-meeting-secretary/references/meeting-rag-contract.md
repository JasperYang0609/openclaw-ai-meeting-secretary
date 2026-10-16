# Meeting RAG contract

Use an existing customer-isolated Gemini RAG installation. This Skill does not create a parallel vector service.

## Fixed production identity

- provider: `google-gemini`
- model: `gemini-embedding-001`
- stable customer ID, source ID, and index project
- customer-separated canonical directory and retrieval route

Do not use Qwen, local embeddings, or another cloud provider as a fallback.

## Approval and source scope

Record who approved sending the exact source scope to Google and when. A product default is not customer approval.

Required source:

- human-confirmed `summary.md`

Optional only with explicit approval:

- cleaned, human-confirmed transcript parts

Always exclude:

- raw audio and video
- SRT or uncorrected transcripts
- drafts and temporary model output
- private chatter
- secrets and credentials
- unapproved attachments

## Access design

`organization-wide` is acceptable only when every indexed meeting may be searched by the whole organization. Sensitive departments require `isolated-route:<name>` or another verified permission-aware retrieval path.

Project labels, source types, frontmatter, and prompts are metadata, not authorization. If the access design is missing, stop with `RAG_PENDING_ACCESS_DESIGN`.

## Canonical directory

```text
records/meetings/
└── YYYY/
    └── <stable-meeting-id>/
        ├── summary.md
        └── transcript-clean.part-001.md  # optional, explicit approval required
```

Notion is a collaboration mirror; confirmed local Markdown is the RAG source of truth.

## Publication gate

1. Meeting record and tasks are human-confirmed.
2. Confirmed Markdown exists under the approved root.
3. `validate_meeting_record.py` passes with required customer identity, index identity, and a fresh meeting-bound confirmation receipt.
4. Existing RAG incremental indexing runs.
5. Receipt readback confirms `google-gemini`, `gemini-embedding-001`, and the expected changed file.
6. Coverage audit passes.
7. A natural-language query based on a unique decision returns the expected source.

Only all seven steps permit `RAG_READY`. The local validators do not execute indexing or authenticate provider readback.

## Correction and withdrawal

- Correction: update the same stable meeting ID, then run incremental indexing, audit, and positive recall.
- Withdrawal: remove the file from the approved source root, then run incremental indexing, audit, and a negative recall test.
- Failure: keep the confirmed local and Notion records, mark `RAG_PENDING` or `RAG_ERROR`, and never change providers silently.
