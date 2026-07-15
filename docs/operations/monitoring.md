# Monitoring

---

## Stack

| Tool | URL | Purpose |
|---|---|---|
| Prometheus | :9090 | Metrics collection (15s scrape) |
| Grafana | :3000 | Dashboards (admin/ragadmin) |
| Flower | :5555 | Celery task monitoring |
| AlertManager | (via Helm) | Alert routing |

---

## Custom Prometheus metrics

| Metric | Type | Labels | Measures |
|---|---|---|---|
| `rag_ask_requests_total` | Counter | `provider` | Total /ask requests |
| `rag_ask_latency_seconds` | Histogram | `provider` | End-to-end /ask latency |
| `rag_retrieval_top1_score` | Histogram | `provider` | Top-1 relevance score |
| `rag_empty_retrievals_total` | Counter | `provider` | Queries returning 0 chunks |
| `rag_ingest_jobs_submitted_total` | Counter | `provider, strategy` | Jobs queued |
| `rag_ingest_jobs_completed_total` | Counter | `provider, strategy, status` | Jobs finished |
| `rag_ingest_chunks_created_total` | Counter | `provider, strategy` | Chunks ingested |
| `rag_vector_store_chunks` | Gauge | `provider` | Live chunk count |
| `rag_llm_generation_latency_seconds` | Histogram | — | Ollama response time |
| `rag_llm_errors_total` | Counter | — | LLM connection errors |

---

## Alert rules

| Alert | Condition | Severity | Action |
|---|---|---|---|
| `RAGAPIDown` | API unreachable 30s | Critical | `kubectl rollout restart deployment/rag-api` |
| `RAGHighAskLatency` | p95 latency > 30s for 2min | Warning | Check Ollama, reduce TOP_K |
| `RAGHighEmptyRetrievals` | >50% queries return 0 chunks | Warning | Re-ingest, check vector store |
| `RAGLLMErrors` | LLM error rate > 0.1/s | Critical | `kubectl logs deployment/rag-api` |
| `RedisDown` | Redis unreachable 30s | Critical | `kubectl rollout restart deployment/redis` |
| `RAGWorkerQueueBacklog` | Queue > 20 jobs for 5min | Warning | KEDA should auto-scale |
| `RAGPodOOMKilled` | Any RAG pod OOM killed | Critical | Increase memory limits |

---

## Useful Prometheus queries

```promql
# Request rate per minute
rate(rag_ask_requests_total[1m]) * 60

# p95 ask latency
histogram_quantile(0.95, rate(rag_ask_latency_seconds_bucket[5m]))

# Empty retrieval rate
rate(rag_empty_retrievals_total[5m]) / rate(rag_ask_requests_total[5m])

# Chunk counts per backend
rag_vector_store_chunks

# Active worker pods (Kubernetes)
kube_deployment_status_replicas_ready{deployment="rag-worker",namespace="rag-system"}

# Redis queue depth
redis_list_length{key="celery"}
```

---

## Generating traffic for dashboards

After a fresh start, run this to populate all metrics:

```bash
bash scripts/generate_traffic.sh
```

Wait 15 seconds then check Prometheus/Grafana — all panels will populate.