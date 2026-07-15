# Vector Store

**File:** `src/vectorstore/store.py`

Factory pattern supporting three backends.
The pipeline never imports backend-specific code directly.

---

## Factory Pattern

```python
store = get_vector_store(provider="chroma")   # or "pinecone" / "mongodb"
store.add_documents(docs, ids=ids)
results = store.similarity_search_with_relevance_scores(query, k=4)
```

One instance is cached per provider (singleton per backend).

---

## Backends

=== "Chroma"

    Local, file-persisted. Zero setup. Best for dev and testing.

```env
    VECTOR_DB_PROVIDER=chroma
    CHROMA_PERSIST_DIR=./data/vectorstore
    CHROMA_COLLECTION_NAME=rag_documents
```

    | Property | Value |
    |---|---|
    | Type | Local file (SQLite + HNSW) |
    | Metric | Cosine (set at collection creation) |
    | Latency | ~5ms |
    | Cost | $0 |
    | Scale | Local disk |
    | Setup | None |

    !!! warning "CVE-2026-45829"
        This vulnerability affects Chroma's HTTP server mode only.
        We use `PersistentClient` (local file mode) exclusively.
        The HTTP server is never started. No network exposure.

=== "Pinecone"

    Serverless cloud vector DB. Best for production demos.

```env
    VECTOR_DB_PROVIDER=pinecone
    PINECONE_API_KEY=your-key
    PINECONE_INDEX_NAME=rag-system-index
```

    **Index requirements:** dim=384, metric=cosine, AWS us-east-1

    Index is **auto-created** if it doesn't exist:

```python
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
```

    | Property | Value |
    |---|---|
    | Type | Managed serverless |
    | Metric | Cosine |
    | Latency | ~50-100ms |
    | Cost | Free tier available |
    | Scale | Unlimited |
    | Setup | API key + account |

=== "MongoDB Atlas"

    MongoDB Atlas Vector Search. Best for teams already on MongoDB.

```env
    VECTOR_DB_PROVIDER=mongodb
    MONGODB_ATLAS_URI=mongodb+srv://...
    MONGODB_DB_NAME=rag_system
    MONGODB_COLLECTION_NAME=document_chunks
    MONGODB_VECTOR_INDEX_NAME=vector_index
```

    **Atlas Vector Search index** must be created manually with:

```json
    {
      "fields": [
        {"type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine"},
        {"type": "filter", "path": "source"},
        {"type": "filter", "path": "doc_id"}
      ]
    }
```

    Uses a **shared `MongoClient` singleton** with `certifi` SSL
    (required on macOS to prevent TLS handshake failures).

    | Property | Value |
    |---|---|
    | Type | Managed cloud |
    | Metric | Cosine |
    | Latency | ~100-300ms |
    | Cost | Free tier M0 (512MB) |
    | Scale | 512MB free |
    | Setup | URI + vector search index |

---

## Switching backends

No restart needed — switch per request:

```bash
# Ingest into Pinecone
curl -X POST http://localhost/ingest \
  -d '{"provider": "pinecone", "strategy": "recursive"}'

# Query Pinecone
curl -X POST http://localhost/ask \
  -d '{"question": "...", "provider": "pinecone"}'
```

Or change the default in `.env`:

```env
VECTOR_DB_PROVIDER=pinecone
```

---

## Reset a collection

```bash
# Wipe and rebuild from scratch
curl -X POST http://localhost/ingest \
  -d '{"provider": "chroma", "reset": true}'
```