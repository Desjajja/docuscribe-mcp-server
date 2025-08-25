# Docuscribe MCP

## Overview
Docuscribe MCP is a tool designed to interact with documentation libraries using MCP (Model Context Protocol). It provides two main tools for querying and fetching content:

1. `list_all_docs`: Retrieves a pageable catalog of all available documentation libraries with stable IDs.
2. `fetch_doc_content`: Fetches content from a specific document in three modes: index, single range, and multi-range.

## Tools

### `list_all_docs`
#### Description
Retrieves a pageable catalog of all available documentation libraries (documents) with stable IDs (uids).

#### Parameters
- `limit` (int, optional): Max number of documents (1..1000, default 100).
- `offset` (int, optional): Pagination offset (>=0, default 0).

#### Returns
A JSON string exactly mirroring backend response:
```json
{
  "documents": [
    {"id": "uuid", "name": "Title", "hashtags": ["tag1", "tag2"]},
    ...
  ]
}
```

#### Usage Guidance
- Call this first to discover a document's stable `id`.
- Use that `id` as `doc_uid` for `fetch_doc_content`.
- Persist (cache) returned ids; they do not change during session.
- Avoid re-calling once ids are known unless searching for new libraries or pagination needed.
- May store multiple ids for multi-source comparison.

#### Examples
- Minimal call:
  ```python
  list_all_docs(limit=50, offset=0)
  ```
- Paginated follow-up:
  ```python
  list_all_docs(limit=100, offset=100)
  ```

### `fetch_doc_content`
#### Description
Fetches documentation content in three modes:
1. **Index Mode**: No parameters -> structural overview (pages, ranges).
2. **Single Range Mode**: `start` + `max_length` -> sequential slice with paging hints (`has_more`, `next_start`).
3. **Multi-Range Mode**: `ranges` parameter -> targeted non-contiguous retrieval.

#### Parameters
- `doc_uid` (str): Stable document ID from `list_all_docs`.
- `start` (int, optional): Starting word index (Single Range Mode).
- `max_length` (int, optional): Max words to return (Single Range).
- `ranges` (str, optional): Comma-separated list of start-end pairs (e.g., "0-100,200-300") for Multi-Range Mode.

#### Returns
A JSON string combining backend `document` and `meta`. Convenience keys `has_more` and `next_start` are surfaced when present.

#### Usage Guidance
- Step 2: After caching `doc_uid`, call Index Mode.
- Analyze pages/ranges to identify candidate section(s).
- If uncertain: begin Single Range at `start=0`; iterate while `has_more` and info not found.
- Use keyword/heading detection to decide early switch to targeted Multi-Range.
- Accumulate content locally; avoid refetching previously retrieved spans.

#### Examples
- Index retrieval:
  ```python
  fetch_doc_content(doc_uid="abc123")
  ```
- Progressive Single Range loop:
  ```python
  fetch_doc_content(doc_uid="abc123", start=0, max_length=500)
  ```
- Multi-Range targeted fetch:
  ```python
  fetch_doc_content(doc_uid="abc123", ranges="0-120,400-550")
  ```

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env.local` file with the following content:
     ```env
     SERVER_BACKEND_URL=http://localhost:9002
     ```

## Running the MCP Server
Start the MCP server:
```bash
python main.py
```

## Real Use Cases
<img width="1582" height="952" alt="image" src="https://github.com/user-attachments/assets/727e96f0-680b-4007-aad0-a6baecafdd14" />


## Notes
- Ensure the backend server is running at the URL specified in `.env.local`.
- Use `list_all_docs` to retrieve document IDs before calling `fetch_doc_content`.
- Cache document IDs to optimize queries and avoid unnecessary lookups.

## License
MIT License
