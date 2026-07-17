# Embeddings

**File:** `src/embedings/embedder.py`

!!! note
    The directory is `src/embedings/` (missing second "d") in this
    codebase — a pre-existing typo left as-is rather than renamed, since
    the module is imported by path in several places and renaming carries
    real risk for zero functional benefit.

---

## Model

| Property | Value |
|---|---|
| Model name | `all-MiniLM-L6-v2` |
| Provider | HuggingFace (local) |
| Dimensions | 384 |
| Max tokens | 256 word pieces (~180 words) |
| Normalization | L2 normalized |
| Device | CPU (no GPU required) |
| Size on disk | ~22MB |
| Cost | $0 — runs entirely locally |

---

## Why this model

| Criterion | all-MiniLM-L6-v2 | all-mpnet-base-v2 | text-embedding-3-small |
|---|---|---|---|
| Dimensions | 384 | 768 | 1536 |
| Model size | 22MB | 420MB | API only |
| CPU inference | ~50ms/batch | ~200ms/batch | ~200ms (network) |
| MTEB score | 56.26 | 57.02 | 62.3 |
| Cost | Free | Free | $0.02/1M tokens |
| **Verdict** | **Selected** | 2x slower | API dependency |

The quality difference between MiniLM and mpnet is marginal (0.76 MTEB points)
but the speed difference is 4x. For a local RAG system, speed wins.

---

## Implementation

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)
```

**Singleton pattern** — the model is expensive to load (~2s).
`get_embeddings()` loads it once and reuses the same instance
across all calls (ingestion + retrieval).

---

## Assumptions & failure modes

!!! warning "Silent failures to watch for"

    | Failure | How it manifests | Fix |
    |---|---|---|
    | Non-English text | Embeddings still produced but similarity unreliable | Use a multilingual model |
    | Chunks >256 tokens | End of chunk silently truncated | Keep `CHUNK_SIZE` ≤ 200 words |
    | Domain jargon | "CI/CD" and "continuous integration" may not cluster | Consider fine-tuning |
    | Numerical content | "€1.2M" and "1,200,000 euros" may not match | Use hybrid BM25 + dense search |

---

## Pre-baking into Docker image

The model is downloaded and cached during `docker build`:

```dockerfile
RUN python -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2')
"
```

This eliminates the cold-start download (80MB) on first API request.