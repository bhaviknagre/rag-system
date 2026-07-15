# Architecture Decision Records

!!! note
    ADRs document every significant design decision — the context,
    options considered, decision made, and consequences.

## ADR-001 — LangChain as Abstraction Layer

**Status:** Accepted

**Context:** Needed to support three vector DB backends with the same
embedding model and retrieval interface. Writing custom adapters for each
would create significant maintenance overhead.

**Decision:** Use LangChain `VectorStore` interface for embeddings and
vector stores only. Not using LangChain chains/agents — only using it
as a thin adapter layer.

**Consequences:**

- ✅ Single `Embeddings` object passed to all three backends unchanged
- ✅ `add_documents()` and `similarity_search()` work identically across backends
- ⚠️ LangChain dependency tree is large (~15 sub-packages)

---

## ADR-002 — Celery + Redis for Background Ingestion

**Status:** Accepted

**Context:** Ingestion involves loading, chunking, embedding (CPU-intensive),
and writing to the vector store. On a large document this takes 30-120 seconds.
Blocking an HTTP thread for this duration causes client timeouts.

**Decision:** Celery + Redis. FastAPI `BackgroundTasks` does not support
retries, result persistence, or monitoring. Celery gives all three plus Flower.

**Consequences:**

- ✅ `POST /ingest` returns in <100ms always
- ✅ Jobs survive API restarts (persisted in Redis)
- ✅ Retry with exponential backoff (max 2 retries)
- ⚠️ Two extra services to operate (Redis + Worker)

---

## ADR-003 — Three Vector DB Backends

**Status:** Accepted

**Context:** Different contexts have different requirements: local dev needs
zero setup, cloud demos need managed infrastructure, teams already on MongoDB
want to avoid a new vendor.

**Decision:** Factory pattern supporting all three, switchable per request.

**Consequences:**

- ✅ No vendor lock-in
- ✅ Same API regardless of backend
- ⚠️ Three codepaths to maintain

---

## ADR-004 — Local LLM via Ollama

**Status:** Accepted

**Context:** Needed an LLM for answer generation. OpenAI costs ~$0.002/query
and requires internet + API key management.

**Decision:** Ollama llama3.2:1b as default. Config-swappable.

**Consequences:**

- ✅ $0 LLM inference cost
- ✅ No API key required
- ⚠️ 1B param model — lower quality than GPT-4o-mini
- ⚠️ Generation latency: 5-30s on CPU

---

## ADR-005 — DVC Separate from Celery

**Status:** Accepted

**Context:** Needed data versioning and reproducible pipelines.
Also needed async API ingestion. These are different concerns.

**Decision:** Both, with intentional separation.

- **DVC** = reproducible experiment pipeline (synchronous)
- **Celery** = async API production pipeline (non-blocking)

**Consequences:**

- ✅ `dvc repro` is deterministic and versioned
- ✅ `POST /ingest` is non-blocking and retryable
- ⚠️ Two ingestion paths to explain