# Chunking Strategies

Three strategies, switchable per request via `strategy` param.

## Recursive (default)

Splits text hierarchically: paragraph → sentence → word → character.

```python
# Switch via API
POST /ingest  {"strategy": "recursive"}

# Switch via .env
CHUNKING_STRATEGY=recursive
```

**When to use:** General documents, PDFs, mixed formats. Fast and deterministic.

**Config:**
```env
CHUNK_SIZE=800      # words per chunk
CHUNK_OVERLAP=150   # overlap between chunks
```

---

## Semantic

Uses embedding similarity to detect topic shifts and split there.
Compares adjacent sentence embeddings — splits when cosine distance
exceeds the 90th percentile threshold.

```python
POST /ingest  {"strategy": "semantic"}
```

**When to use:** Research papers, reports with clear topic transitions.
Produces semantically coherent chunks but is slower (runs embeddings
during chunking itself).

!!! warning "Performance"
    Semantic chunking is ~10-20x slower than recursive because it runs
    the embedding model on every sentence during the chunking phase.

---

## Sentence Window

Each chunk = one sentence. Surrounding `window_size=2` sentences stored
in `window_context` metadata field. At query time the LLM receives both
the matched sentence and its surrounding context.

```python
POST /ingest  {"strategy": "sentence_window"}
```

**When to use:** Q&A systems, fact retrieval, legal documents.

**How window context works:**

```bash
Sentences: [1] [2] [3] [4] [5]
↑
chunk = sentence 3
window_context = sentences 1,2,4,5
```
---

## Comparison

| | Recursive | Semantic | Sentence Window |
|---|---|---|---|
| Speed | Fast | Slow | Medium |
| Chunks per 500-word doc | 30-50 | 20-35 | 100-300 |
| Context preservation | Good (overlap) | Excellent | Good (window) |
| Best for | General | Research papers | Q&A |