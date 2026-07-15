# RAG System

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Production-Grade RAG**

    ---

    Full Retrieval-Augmented Generation pipeline from document ingestion
    to grounded LLM answers, deployed at scale.

    [:octicons-arrow-right-24: Quickstart](guides/quickstart.md)

-   :material-database:{ .lg .middle } **Multi-Backend Vector Store**

    ---

    Switch between Chroma, Pinecone, and MongoDB Atlas with a single
    API parameter — no code changes needed.

    [:octicons-arrow-right-24: Vector Store](components/vectorstore.md)

-   :material-kubernetes:{ .lg .middle } **Kubernetes Ready**

    ---

    Full K8s deployment with KEDA queue-based autoscaling, HPA,
    Ingress routing, and Prometheus monitoring.

    [:octicons-arrow-right-24: Kubernetes](kubernetes/overview.md)

-   :material-chart-line:{ .lg .middle } **Full Observability**

    ---

    Prometheus metrics, Grafana dashboards, Flower task monitoring,
    and 7 alert rules out of the box.

    [:octicons-arrow-right-24: Monitoring](operations/monitoring.md)

</div>

---

## What is this?

The RAG System is a production-grade pipeline that:

1. **Ingests** documents (PDF, DOCX, TXT) into a vector store
2. **Retrieves** the most semantically relevant chunks for any query
3. **Generates** grounded answers using a local LLM — zero API cost

POST /ask  {"question": "What is this document about?"}
→  {"answer": "...", "sources": [...]}

```bash
Client → Nginx → FastAPI (HPA: 2→10)
│
Redis ← Celery Workers (KEDA: 0→10)
│
Loader → Chunker → Embedder → Vector Store
│
Ollama (llama3.2:1b)
```

See [Architecture Diagrams](architecture/diagrams.md) for the full visual
reference — system topology, ingestion/query sequence diagrams, monitoring
flow, and Kubernetes topology.

## Versions

| Version | Description |
|---|---|
| `v1.0.0` | Basic RAG — Chroma + Ollama + FastAPI + DVC |
| `v2.0.0` | LangChain + Pinecone + MongoDB + advanced chunking |
| `v2.1.0` | Celery + Redis background jobs + Flower |
| `v2.2.0` | Nginx + Prometheus + Grafana + Gunicorn + auto-scaling |
| `v2.2.2-k8s` | Full Kubernetes — KEDA + HPA + Ingress |