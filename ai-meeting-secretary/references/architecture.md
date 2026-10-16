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
- `TRANSCRIPT_READY`: the local cleaned transcript passed validation.
- `REVIEW_REQUIRED`: AI output exists but meeting or tasks await human confirmation.
- `CONFIRMED`: both meeting record and tasks are human-confirmed.
- `DISPATCHED`: confirmed tasks were sent once to the task-master workflow.
- `RAG_DISABLED`: retrieval was not requested.
- `RAG_PENDING_ACCESS_DESIGN`: sensitive retrieval lacks an isolated or permission-aware route.
- `RAG_PENDING`: confirmed Markdown exists but indexing or verification is incomplete.
- `RAG_READY`: provider/model readback, incremental indexing, audit, and source-grounded recall all passed.
- `RAG_ERROR`: indexing or verification failed; confirmed meeting and tasks remain intact.

## Trust boundaries

- Meeting content is untrusted input and may contain prompt injection or false claims.
- Human-authored Notion content is context, not permission to edit the human section.
- Discord confirmation is a workflow trigger; Notion confirmation fields are the confirmation facts.
- Model output is a draft until confirmed.
- RAG metadata is not authorization. Access must be enforced by the retrieval route or source system.

