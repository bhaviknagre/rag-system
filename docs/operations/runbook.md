# Operational Runbook

---

## Common operations

### Ingest new documents

```bash
# Drop files in data/raw/
cp your_docs/*.pdf data/raw/

# Via API (non-blocking)
curl -X POST http://localhost/ingest \
  -d '{"provider": "chroma", "strategy": "recursive", "reset": false}'

# Poll until success
curl http://localhost/jobs/<job_id>

# Via DVC (tracked + reproducible)
dvc add data/raw && dvc repro
```

### Switch vector DB backend

```bash
# Single query — no restart needed
curl -X POST http://localhost/ask \
  -d '{"question": "...", "provider": "pinecone"}'

# Permanent default — restart API
echo "VECTOR_DB_PROVIDER=pinecone" >> .env
docker compose restart rag-api
```

### Rebuild vector store from scratch

```bash
curl -X POST http://localhost/ingest \
  -d '{"provider": "chroma", "reset": true}'
```

---

## Debugging guide

| Symptom | First check | Likely cause | Fix |
|---|---|---|---|
| `/ask` returns "Unable to connect to Ollama" | `docker logs rag-ollama` | Ollama not ready or model not pulled | `docker exec rag-ollama ollama pull llama3.2:1b` |
| Job stays `queued` forever | `docker compose ps \| grep worker` | Worker container not running | `docker compose up -d rag-worker` |
| Flower shows no workers | `docker compose logs rag-worker` | Worker crashed on startup | Check for ModuleNotFoundError |
| MongoDB returns empty results | Atlas console → Network Access | IP not whitelisted | Add `0.0.0.0/0` in Network Access |
| Prometheus shows no data | http://localhost:9090/targets | Scrape target down | Check container is healthy |
| Grafana shows "No data" | Run `generate_traffic.sh` first | No requests made yet | Generate traffic, wait 15s |
| `dvc repro` errors | `cat dvc.lock` | Stale lock file | `dvc repro --force` |

---

## Kubernetes quick commands

```bash
# View all pods
kubectl get pods -n rag-system

# Watch pods in real time
kubectl get pods -n rag-system -w

# Check HPA
kubectl get hpa -n rag-system

# Check KEDA
kubectl get scaledobject -n rag-system

# API logs
kubectl logs -n rag-system deployment/rag-api --tail=50

# Worker logs
kubectl logs -n rag-system deployment/rag-worker --tail=50

# Shell into API pod
kubectl exec -it -n rag-system deployment/rag-api -- bash

# Check Ollama model
kubectl exec -n rag-system ollama-0 -- ollama list

# Restart deployment
kubectl rollout restart deployment/rag-api -n rag-system

# Zero-downtime rollout after code change
bash k8s/scripts/rollout.sh

# Full teardown
kubectl delete namespace rag-system
kubectl delete namespace monitoring
```

---

## DVC workflow

```bash
# Run full pipeline
dvc repro

# Compare metrics between runs
dvc metrics diff

# See what params changed
dvc params diff

# Visualize pipeline
dvc dag

# Add new documents and rerun
dvc add data/raw
dvc repro
```