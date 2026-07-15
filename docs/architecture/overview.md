# System Architecture

## Architecture Pattern

!!! info "Pattern"
    **Microservices with Event-Driven Background Processing**
    Layered architecture with clean separation between Ingestion,
    Retrieval, and Generation concerns.

## System Components

| Component | Technology | Version | Port |
|---|---|---|---|
| Load Balancer | Nginx | 1.27-alpine | 80 |
| API Server | FastAPI + Gunicorn | 0.139.0 / 23.0.0 | 8000 |
| Worker | Celery | 5.3.6 | — |
| Message Broker | Redis | 7.2-alpine | 6379 |
| Job Monitor | Flower | 2.0.1 | 5555 |
| Embedding Model | sentence-transformers | 3.3.1 | in-process |
| LLM | Ollama llama3.2:1b | latest | 11434 |
| Vector Store 1 | ChromaDB | 0.5.23 | file |
| Vector Store 2 | Pinecone | serverless | HTTPS |
| Vector Store 3 | MongoDB Atlas | M0 free | HTTPS |
| LLM Framework | LangChain | 0.3.30 (core 0.3.86) | library |
| Data Versioning | DVC | 3.50.1 | CLI |
| Metrics | Prometheus | v2.55.1 | 9090 |
| Dashboards | Grafana | 11.4.0 | 3000 |

Exact pins live in `requirements.txt`; see the
[Security guide](../guides/security.md) for the current audit status.

## Two Pipelines

=== "Ingestion (Async)"

```bash
POST /upload or POST /ingest
          │
     FastAPI validates + saves file
          │  returns job_id (HTTP 202)
       Redis (job queue)
          │
    Celery Worker picks up task
          │
   Loader → Chunker → Embedder → Vector Store
```
=== "Query (Sync)"

```bash
POST /ask {question, provider, top_k}
          │
     FastAPI validates
          │
      Retriever
     embeds query → similarity_search(top_k)
          │
   Context Builder (source-tagged)
          │
   Ollama llama3.2:1b → answer
          │
Response {answer, sources[]}
```

## Why Microservices

| Concern | Monolith | Microservices |
|---|---|---|
| Ingestion load | Blocks HTTP thread 30-60s | Celery worker handles async |
| Scaling | Scale entire app | Scale workers independently |
| LLM serving | LLM loaded in app process | Ollama separate process |
| Vector DB | Hard-coded to one store | Factory pattern, 3 backends |
| Fault isolation | Worker crash = API crash | Worker crash = jobs retry |