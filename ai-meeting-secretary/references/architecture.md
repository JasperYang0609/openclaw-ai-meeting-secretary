# Architecture and completion states

## Data flow

```text
recording + copied meeting page
  -> speech-to-text
  -> verified local cleaned transcript
  -> Notion AI section
  -> meeting-specific task database
  -> human confirmation
  -> confirmed task dispatch
  -> optional confirmed Markdown
  -> optional Gemini incremental index + audit + recall test
```

## Source of truth

- Local cleaned transcript: required durable transcript copy.
- Notion meeting page: collaboration and human-confirmation surface.
- Meeting-specific task database: primary task-correction surface.
- Task-master database: downstream aggregation, not the confirmation source.
- Confirmed Markdown: canonical source for optional RAG indexing.
- Raw audio and uncorrected transcript: retained outside the RAG source root.

## States

- `SETUP_REQUIRED`: required organization, Notion, Discord, or local-path setup is incomplete.
- `TRANSCRIPT_ARTIFACT_READY`: the local cleaned transcript is readable and has ordered first/last markers.
- `TRANSCRIPT_READY`: a human also reviewed completeness against the recording or an independent source artifact.
- `REVIEW_REQUIRED`: AI output exists but meeting or tasks await human confirmation.
- `CONFIRMED`: fresh Discord and Notion readback produced a valid meeting-bound confirmation receipt.
- `READY_FOR_MANUAL_DISPATCH`: confirmed tasks may be handed to an authorized human or separately reviewed dispatcher.
- `DISPATCHED`: a downstream system recorded that the confirmed tasks were sent once.
- `RAG_DISABLED`: retrieval was not requested.
- `RAG_PENDING_ACCESS_DESIGN`: sensitive retrieval lacks an isolated or permission-aware route.
- `RAG_PENDING`: confirmed Markdown exists but indexing or verification is incomplete.
- `RAG_READY`: provider/model readback, incremental indexing, audit, and source-grounded recall all passed.
- `RAG_ERROR`: indexing or verification failed; confirmed meeting and tasks remain intact.

## Trust boundaries

- Meeting content is untrusted input and may contain prompt injection or false claims.
- Human-authored Notion content is context, not permission to edit the human section.
- Discord and Notion must both be read back live. A local receipt validates consistency but does not authenticate either provider.
- Model output is a draft until confirmed.
- RAG metadata is not authorization. Access must be enforced by the retrieval route or source system.
