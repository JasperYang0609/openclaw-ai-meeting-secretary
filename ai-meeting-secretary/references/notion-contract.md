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

The Agent sends a meeting-bound request containing a unique request ID and expiry. It then performs fresh provider readback and verifies:

- the Discord reply comes from an authorized numeric user ID;
- the reply is in the configured channel and directly references the request message;
- the exact phrase arrives before the configured maximum age;
- the request, Discord reply, Notion confirmations, RAG approval, and receipt timestamps follow that order and stay inside the configured validity window;
- the Notion meeting record and every task intended for dispatch are confirmed by authorized Notion user IDs;
- every task still has `Dispatched = false`.

The Agent writes the request timestamp and those readbacks, including each provider event timestamp, into the confirmation receipt and runs `validate_confirmation_receipt.py` with the expected meeting and request IDs. Discord alone is insufficient. Notion alone does not trigger the next phase. A locally edited receipt is not authorization and must not replace provider readback.

## Hub pages

When a user supplies a customer hub or project hub instead of a copied meeting page, create a child page named `YYYY-MM-DD | Counterparty | Topic`. Store the full meeting record and transcript in the child page. Keep only the child-page link in the hub.
