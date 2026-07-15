# Retrieval

**File:** `src/vectorstore/store.py` — `query_store()`

`src/pipeline.py` calls `query_store()` directly for every `/ask` request.

!!! note "`src/retrieval/retriever.py` is not on the live request path"
    A separate `Retriever` class exists in `src/retrieval/retriever.py` but
    is not imported by `pipeline.py` or `api/main.py` — the only reference
    to it left in the codebase is `generator.py`'s standalone `__main__`
    test block. It also calls a `.query()` method that the LangChain
    `VectorStore` interface doesn't expose (the real method is
    `similarity_search_with_relevance_scores`), so running it directly
    raises `AttributeError`. It's dead code, not a hidden alternate path —
    documented here so it isn't mistaken for the real retrieval layer.

---

## How retrieval works

```python
# 1. Embed the query
query_vector = embedder.embed_query("What is this document about?")
# → 384-dimensional vector, same space as document chunks

# 2. Similarity search
results = store.similarity_search_with_relevance_scores(
    query=query_text,
    k=top_k
)
# → [(Document, score), ...] top_k results

# 3. Return structured results
[{
    "text": "chunk text",
    "doc_id": "filename.pdf",
    "source": "data/raw/filename.pdf",
    "score": 0.87,
    "window_context": "",   # populated by sentence_window strategy
    "strategy": "recursive"
}]
```

---

## Context building

For the LLM prompt, chunks are formatted with source attribution:

=== "Recursive / Semantic"

[Source 1: filename.pdf]
The chunk text goes here...

[Source 2: other.pdf]
Another relevant chunk...

=== "Sentence Window"

    The surrounding context is prepended so the LLM has the full picture
    even though retrieval matched on a single sentence:

---

## Retrieval failure modes

!!! danger "Where retrieval fails silently"

    **Semantic gap** — Query uses different vocabulary than the document.
    "What are the hosting expenses?" fails if doc says "infrastructure cost."

    **Fix:** Use semantic chunking, or add query expansion.

    ---

    **Stale vector store** — Document updated on disk but old chunks returned.

    **Fix:** `POST /ingest` with `reset=true` after updates.
    DVC detects `data/raw` changes automatically via `dvc repro`.

    ---

    **Cross-document reasoning** — Answer requires combining info from
    two different documents. Each chunk retrieved independently.

    **Fix:** Increase `TOP_K` so both documents appear in context.

    ---

    **Chunk too large** — Relevant answer buried in 500-word chunk.

    **Fix:** Reduce `CHUNK_SIZE` in `.env` (try 200-300 for dense factual content).

    ---

    **MongoDB empty results** — Atlas Vector Search index not Active yet.

    **Fix:** Check Atlas console — wait for index status to show Active.

---

## Config

```env
TOP_K=4            # chunks retrieved per query (1-20 via API)
```