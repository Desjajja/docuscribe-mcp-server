import httpx
import json
from mcp.server.fastmcp import FastMCP
from typing import Optional
import os
from dotenv import load_dotenv
from urllib.parse import urljoin

load_dotenv(dotenv_path=".env.local")
backend_url = os.getenv("SERVER_BACKEND_URL", "http://localhost:9002")
# Initialize FastMCP server
mcp = FastMCP("Docuscribe")


LIST_DOCS_URL = urljoin(backend_url, "/api/list_all_docs")  # New list endpoint
BASE_FETCH_URL = urljoin(backend_url, "/api/fetch_doc_content")  # Base for fetch modes


@mcp.tool()
async def list_all_docs(limit: int = 100, offset: int = 0) -> str:
    """
    Retrieve pageable catalog of all available documentation libraries (documents) with stable IDs (uids).

    Parameters:
        limit (int, optional): Max number of documents (1..1000, default 100).
        offset (int, optional): Pagination offset (>=0, default 0).

    Returns:
        str: JSON string exactly mirroring backend response:
            {
              "documents": [
                {"id": "uuid", "name": "Title", "hashtags": ["tag1", "tag2"]},
                ...
              ]
            }

    Usage guidance for LLMs:
        - Call this first to discover a document's stable `id`.
        - Use that `id` as `doc_uid` for `fetch_doc_content`.
        - Persist (cache) returned ids; they do not change during session.
        - Avoid re-calling once ids are known unless searching for new libraries or pagination needed.
        - May store multiple ids for multi-source comparison.

    Workflow:
        Step 1: Call once; store target doc_uid(s).

    Examples:
        Minimal call:
            list_all_docs(limit=50, offset=0)
        Paginated follow-up:
            list_all_docs(limit=100, offset=100)

    Efficiency / Anti-patterns:
        - Don’t call before every content fetch.
        - Don’t loop through pages unless necessary.

    Error Handling:
        - HTTP failure -> error object.
        - Empty list scenario.

    Follow-on Tools:
        - Next: fetch_doc_content in index mode with chosen doc_uid.
    """
    # Normalize + clamp inputs
    if limit < 1:
        limit = 1
    if limit > 1000:
        limit = 1000
    if offset < 0:
        offset = 0

    url = f"{LIST_DOCS_URL}?limit={limit}&offset={offset}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return json.dumps(
                {"error": "list_all_docs failed", "status": resp.status_code},
                ensure_ascii=False,
            )
        try:
            data = resp.json()
        except ValueError:
            return json.dumps(
                {"error": "Failed to decode JSON from list_all_docs"},
                ensure_ascii=False,
            )
        # Return exactly what backend gave (plus normalized limit/offset echo for convenience)
        data["_request"] = {"limit": limit, "offset": offset}
        return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def fetch_doc_content(
    doc_uid: str,
    start: Optional[int] = None,
    max_length: Optional[int] = None,
    ranges: Optional[str] = None,
) -> str:
    """
    Retrieve documentation content in three modes: index, single range, multi-range.

    Parameters:
        doc_uid (str): Stable document ID from `list_all_docs`.
        start (int, optional): Starting word index (Single Range Mode). If provided (or max_length provided), Single Range Mode is used unless `ranges` is also set.
        max_length (int, optional): Max words to return (Single Range). Default (when Single Mode chosen) = 10000. Capped at 50000.
        ranges (str, optional): Comma-separated list of start-end pairs (e.g. "0-100,200-300") for Multi-Range Mode.

    Mode selection logic:
        - If `ranges` is provided -> Multi-Range Mode.
        - Else if `start` is not None or `max_length` is not None -> Single Range Mode (missing values get defaults).
        - Else -> Index Mode.

    Returns:
        str: JSON string combining backend `document` and `meta`. Convenience keys `has_more` and `next_start` are surfaced when present.

    LLM Iteration Guidance:
        - Step 2: After caching doc_uid, call Index Mode.
        - Analyze pages/ranges to identify candidate section(s).
        - If uncertain: begin Single Range at start=0; iterate while has_more and info not found.
        - Use keyword/heading detection to decide early switch to targeted Multi-Range.
        - Accumulate content locally; avoid refetching previously retrieved spans.

    Workflow:
        - Index Mode first after obtaining doc_uid to map structure & locate sections.
        - Single Range for linear exploration or reading contiguous section progressively.
        - Multi-Range for focused extraction of known disjoint sections (after analyzing index or prior slices).

    Examples:
        Index retrieval:
            fetch_doc_content(doc_uid="abc123")
        Progressive Single Range loop:
            fetch_doc_content(doc_uid="abc123", start=0, max_length=500)
        Multi-Range targeted fetch:
            fetch_doc_content(doc_uid="abc123", ranges="0-120,400-550")

    Efficiency / Anti-patterns:
        - Avoid re-fetching index repeatedly.
        - Don’t blindly page through entire doc if section located early.
        - Avoid huge max_length unless justified.

    Stop Criteria:
        - Found required info.
        - has_more == False.
        - Budget/token constraints.
        - Confidence threshold reached.

    Error Handling:
        - Unknown doc_uid -> error.
        - HTTP failure -> status + message.
        - JSON decode failure.
        - Invalid ranges (surface backend error).

    Follow-on Actions:
        - Summarize / extract / compare across multiple doc_uids if cached.
    """
    # Verify document exists (lightweight list fetch). If performance becomes an issue, remove or cache.
    docs_raw = await list_all_docs(limit=1000, offset=0)
    try:
        docs_data = json.loads(docs_raw)
        documents = docs_data.get("documents", [])
    except Exception:
        documents = []
    if not any(d.get("id") == doc_uid for d in documents):
        return json.dumps(
            {"error": f"Document '{doc_uid}' not found"}, ensure_ascii=False
        )

    # Determine mode & build URL
    params = []
    if ranges:
        # Multi-Range Mode
        params.append(f"ranges={ranges}")
    else:
        # Single Range Mode if either provided
        if start is not None or max_length is not None:
            if start is None:
                start = 0
            if start < 0:
                start = 0
            if max_length is None:
                max_length = 10000
            if max_length < 1:
                max_length = 1
            if max_length > 50000:
                max_length = 50000
            params.append(f"start={start}")
            params.append(f"max_length={max_length}")
        # else Index Mode (no params)

    query = ("?" + "&".join(params)) if params else ""
    url = f"{BASE_FETCH_URL}/{doc_uid}{query}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return json.dumps(
                {"error": "fetch_doc_content failed", "status": resp.status_code},
                ensure_ascii=False,
            )
        try:
            data = resp.json()
        except ValueError:
            return json.dumps(
                {"error": "Failed to decode JSON from fetch_doc_content"},
                ensure_ascii=False,
            )

    document = data.get("document", {})
    meta = data.get("meta", {})

    # Convenience extraction
    result = {
        "document": document,
        "meta": meta,
    }
    if "has_more" in meta:
        result["has_more"] = meta.get("has_more")
    if "next_start" in meta:
        result["next_start"] = meta.get("next_start")

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
