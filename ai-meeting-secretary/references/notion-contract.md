# Notion contract

## Required targets

- Transcript database
- Meeting-record database
- Task-master database
- One department task target per configured department
- Master meeting template page

## Meeting page boundary

Each copied meeting page must contain:

1. A human section that the AI may read but never modify.
2. A stable AI marker.
3. An AI-writable section below the marker.
4. A meeting-specific task database.

If the marker is missing or duplicated, stop instead of guessing the writable range.

## Meeting record fields

- Meeting title
- Meeting date
- Meeting category
- Participants
- Transcript link or reference
- Meeting record confirmed
- Meeting confirmed by
- Discord reply state

## Meeting task fields

- Task name and description
- Department and owner
- Deadline and status
- Source meeting and source topic
- Transcript evidence
- Task confirmed
- Task confirmed by
- Dispatched

## Confirmation rule

Discord receives the confirmation phrase, then the Agent reads Notion and verifies that the meeting record and every task intended for dispatch are confirmed by a named human. Discord alone is insufficient. Notion alone does not trigger the next phase.

## Hub pages

When a user supplies a customer hub or project hub instead of a copied meeting page, create a child page named `YYYY-MM-DD | Counterparty | Topic`. Store the full meeting record and transcript in the child page. Keep only the child-page link in the hub.

