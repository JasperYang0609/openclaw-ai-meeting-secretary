---
schema: ai_meeting_secretary.meeting_record.v1
document_type: meeting_summary
meeting_id: example-organization-YYYY-MM-DD-topic
customer_id: example-organization
company: Example Organization
meeting_date: YYYY-MM-DD
title: Meeting title
record_status: draft
confirmed_by_id: REPLACE_WITH_NOTION_USER_ID
confirmed_at: YYYY-MM-DDTHH:MM:SSZ
confirmation_receipt_id: REPLACE_WITH_CONFIRMATION_RECEIPT_ID
rag_approval: pending
rag_approved_by_id: REPLACE_WITH_APPROVER_ID
rag_approved_at: YYYY-MM-DDTHH:MM:SSZ
rag_approval_receipt_id: REPLACE_WITH_RAG_APPROVAL_RECEIPT_ID
access_scope: organization-wide
index_project: ExampleOrganizationMeetings
notion_url: https://www.notion.so/example
---

# YYYY-MM-DD | Meeting title

## Meeting summary

Summarize the purpose, background, and confirmed outcome.

## Decisions

- Decision one and its conditions.
- Decision two and its conditions.

## Action items

- [ ] Task | owner or department | deadline | transcript or topic evidence

## Needs confirmation

- None, or list items that still require a human decision.

## Source integrity

- Source: human-confirmed meeting page.
- Transcript coverage: complete, or describe the known gap without inventing content.
- Excluded: raw audio, uncorrected transcript, private chatter, secrets, and unapproved attachments.
