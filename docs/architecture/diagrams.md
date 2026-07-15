# Architecture Diagrams

Visual reference for the two request flows, the monitoring pipeline, and
the full system topology. Diagrams render natively from the Markdown
source below — no external image assets to keep in sync.

---

## System topology

```mermaid
flowchart TB
    client(["Client"])

    subgraph edge["Edge"]
        nginx["Nginx\nrate limiting + LB"]
    end

    subgraph compute["Compute (scalable)"]
        api1["rag-api #1\nFastAPI + Gunicorn"]
        api2["rag-api #N"]
        worker1["rag-worker #1\nCelery"]
        worker2["rag-worker #N"]
    end

    subgraph data["Data + Messaging"]
        redis[("Redis\nbroker + result backend")]
        vs[("Vector Store\nChroma / Pinecone / MongoDB")]
    end

    subgraph infer["Inference"]
        ollama["Ollama\nllama3.2:1b"]
    end

    subgraph obs["Observability"]
        flower["Flower :5555"]
        prom[("Prometheus :9090")]
        grafana["Grafana :3000"]
    end

    client --> nginx
    nginx --> api1
    nginx --> api2

    api1 <--> redis
    api2 <--> redis
    redis <--> worker1
    redis <--> worker2

    api1 --> vs
    api2 --> vs
    worker1 --> vs
    worker2 --> vs

    api1 --> ollama
    api2 --> ollama

    worker1 -. events .-> flower
    worker2 -. events .-> flower

    api1 -. /metrics .-> prom
    api2 -. /metrics .-> prom
    prom --> grafana
```

---

## Ingestion flow (async)

Ingestion never blocks the HTTP thread — `POST /ingest` and `POST /upload`
both hand off to Celery and return immediately with a `job_id`.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant N as Nginx
    participant A as FastAPI (rag-api)
    participant R as Redis (broker)
    participant W as Celery Worker
    participant V as Vector Store

    C->>N: POST /ingest {provider, strategy, reset}
    N->>A: proxy
    A->>R: apply_async(ingest_documents_task)
    A-->>C: 202 Accepted {job_id, status: queued}

    R->>W: deliver task
    W->>W: update_state(PROGRESS, "loading documents")
    W->>W: Loader -> Chunker -> Embedder
    W->>V: add_documents(chunks)
    V-->>W: ack
    W->>R: state = SUCCESS {chunks_added, total_chunks}

    C->>N: GET /jobs/{job_id}
    N->>A: proxy
    A->>R: AsyncResult(job_id)
    R-->>A: state + result
    A-->>C: {status: success, result: {...}}
```

**Failure path:** if the task raises, the worker retries up to 2 times
with exponential backoff (`2^n` seconds). A `SoftTimeLimitExceeded`
(10 minutes) is treated as terminal and marks the job `failed` immediately
rather than retrying — see `src/worker/tasks.py`.

---

## Query flow (sync)

`POST /ask` is synchronous end-to-end — the client waits for retrieval
and generation to complete in one request.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant N as Nginx
    participant A as FastAPI (rag-api)
    participant V as Vector Store
    participant O as Ollama

    C->>N: POST /ask {question, provider, top_k}
    N->>A: proxy
    A->>V: similarity_search_with_relevance_scores(query, k)
    V-->>A: [(chunk, score), ...]
    A->>A: build source-tagged context
    A->>O: POST /api/generate {model, prompt}
    O-->>A: {response}
    A-->>C: {answer, sources[]}
```

**Failure path:** if Ollama is unreachable or times out, `Generator.generate()`
catches the error and returns a plain-text error message as the `answer`
field — the HTTP response is still `200 OK` with valid JSON, so callers
must check the *content* of `answer`, not just the status code.

---

## Monitoring flow

```mermaid
flowchart LR
    api["rag-api /metrics"] -->|scrape 15s| prom[("Prometheus")]
    redisExp["redis-exporter :9121"] -->|scrape| prom
    nginxExp["nginx-exporter :9113"] -->|scrape| prom
    worker["Celery worker events"] -->|real-time| flower["Flower :5555"]
    prom -->|datasource| grafana["Grafana :3000"]
    prom -->|alert rules| alertmgr["Alerting\n(Prometheus rules)"]
```

---

## Vector store factory

The pipeline code never imports a backend-specific client — `get_vector_store()`
resolves and caches one instance per provider, so `chroma`, `pinecone`, and
`mongodb` are switchable per-request with identical calling code.

```mermaid
flowchart LR
    req["provider param\n(chroma / pinecone / mongodb)"] --> factory{{"get_vector_store()"}}
    factory -->|cached?| cache[("_store_instances\nsingleton per provider")]
    factory -->|cold start| build["BACKEND_MAP[provider]()"]
    build --> chroma["_build_chroma()"]
    build --> pinecone["_build_pinecone()"]
    build --> mongo["_build_mongodb()"]
    chroma --> cache
    pinecone --> cache
    mongo --> cache
```

Note: MongoDB's client is constructed lazily on first use, not at module
import — this keeps `chroma`-only deployments from requiring a
`MONGODB_ATLAS_URI` just to boot.

---

## Kubernetes topology (Minikube)

```mermaid
flowchart TB
    subgraph ns_rag["namespace: rag-system"]
        ing["Ingress\nrag.local"]
        apiDep["rag-api Deployment\nHPA 2→10"]
        workerDep["rag-worker Deployment\nKEDA 0→10"]
        redisDep["Redis Deployment + PVC"]
        ollamaSS["Ollama StatefulSet + PVC"]
        flowerDep["Flower Deployment"]
    end

    subgraph ns_mon["namespace: monitoring"]
        promOp["Prometheus (Helm)"]
        graf["Grafana (Helm)"]
    end

    subgraph ns_keda["namespace: keda"]
        kedaOp["KEDA Operator"]
    end

    ing --> apiDep
    ing --> flowerDep
    ing --> graf
    ing --> promOp

    apiDep <--> redisDep
    workerDep <--> redisDep
    apiDep --> ollamaSS
    workerDep --> ollamaSS

    kedaOp -.watches queue depth.-> workerDep
    promOp -.scrapes.-> apiDep
    promOp -.scrapes.-> workerDep
```
