# Name Suggestion While Typing (Design)

## Problem

Current search requires users to know and type exact Wikidata QIDs (e.g. `Q34660`), which is hard for normal users.  
Need real-time name suggestions while typing, but keep BFS search API compatibility (`start`, `target` are QIDs).

## Scope

1. Add real-time suggestions for both input fields: **BẮT ĐẦU** and **ĐÍCH ĐẾN**.
2. Suggestions combine:
   - Wikidata name search results
   - Existing global history (Redis-backed)
3. UI shows human-readable name, but selected value carries hidden `qid` for search requests.
4. Backward compatibility: manual QID typing must still work.

## Architecture

### Backend

1. Add a new Wikidata client/service method using `wbsearchentities` API:
   - Input: query text, limit
   - Output: normalized items `{ qid, label, description, source }`
2. Add helper to transform history records into suggestion-like items.
3. Add new endpoint:
   - `GET /api/suggestions?q=<text>&limit=<n>`
   - Combines Wikidata + history
   - Deduplicates by `qid`
   - Returns ranked list

### Frontend

1. For each input field, track:
   - display text
   - selected suggestion (`qid`, `label`)
   - suggestions list
2. On typing:
   - debounce request (~300ms)
   - call `/api/suggestions` when input length >= 2
3. On suggestion click:
   - fill display label
   - store selected `qid` internally
4. On search click:
   - use selected `qid` when available
   - otherwise use raw typed value (supports manual QID)

## Data Flow

1. User types text in start/target input.
2. Frontend calls `/api/suggestions`.
3. Backend fetches/merges Wikidata + history suggestions and returns JSON.
4. Frontend renders dropdown.
5. User selects suggestion.
6. Search request sends QIDs to existing `/api/search`.

## Error Handling

1. Suggest API failure:
   - frontend hides dropdown and keeps normal input behavior.
2. Wikidata search failure:
   - backend still returns history-based suggestions when possible.
3. Empty query:
   - return empty array quickly (no external call).

## Testing Strategy

1. Backend manual checks:
   - `/api/suggestions?q=row` returns valid list.
   - Works when Redis has history and when history is empty.
2. Frontend manual checks:
   - typing shows suggestions for both fields.
   - selecting item sets hidden QID.
   - search uses QID and existing graph flow still works.
3. Regression checks:
   - direct QID typing still works.
   - `/api/history` and `/api/search` behavior remains unchanged.

## Out of Scope

1. Keyboard navigation in suggestion dropdown (up/down/enter).
2. Pagination/infinite scroll for suggestions.
3. Advanced relevance scoring beyond simple rank + dedupe.
