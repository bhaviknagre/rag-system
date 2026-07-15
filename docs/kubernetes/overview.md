# Kubernetes Overview

**Version:** v2.3.0-k8s | **Platform:** Minikube (local)

The full RAG stack runs on Kubernetes with automatic scaling,
queue-based worker autoscaling via KEDA, and path-based ingress routing
to all services via a single hostname `http://rag.local`.

---

## Why Kubernetes

| Concern | Docker Compose | Kubernetes |
|---|---|---|
| Auto-scaling | Manual `--scale` | HPA + KEDA automatic |
| Self-healing | `restart: unless-stopped` | Pod rescheduling on any node |
| Rolling updates | Full restart | Zero-downtime `RollingUpdate` |
| Config management | `.env` file on disk | ConfigMap + Secret |
| Health routing | Basic healthcheck | Liveness + Readiness + Startup probes |
| Resource enforcement | Soft limits | Hard CPU/memory limits per pod |

---

## Three Namespaces

rag-system      ← all RAG workloads (API, workers, Redis, Ollama, Flower)
monitoring      ← Prometheus, Grafana, AlertManager (Helm release)
keda            ← KEDA operator + Metrics APIServer (Helm release)

---

## Access URLs

| URL | Service | Auth |
|---|---|---|
| http://rag.local | FastAPI API | None |
| http://rag.local/docs | Swagger UI | None |
| http://rag.local/rag-system | RAG Web UI | None |
| http://rag.local/flower | Celery Monitor | None |
| http://rag.local/grafana | Grafana | admin / ragadmin |
| http://rag.local/prometheus | Prometheus | None |

---

## Prerequisites

```bash
brew install minikube kubectl helm

minikube start \
  --driver=docker \
  --cpus=4 \
  --memory=6144 \
  --disk-size=20g

minikube addons enable ingress
minikube addons enable metrics-server
```

---

## One-command deploy

```bash
bash k8s/scripts/build-images.sh
bash k8s/scripts/deploy.sh
sudo bash k8s/scripts/setup-hosts.sh
minikube tunnel    # keep this running
```

---

## Cloud portability

These manifests are cloud-portable. Two changes to go to production:

| Setting | Minikube | GKE | EKS | AKS |
|---|---|---|---|---|
| `imagePullPolicy` | `Never` | `Always` + gcr.io | `Always` + ECR | `Always` + ACR |
| `storageClassName` | `standard` | `pd-standard` | `gp2` | `managed-premium` |
| Everything else | identical | identical | identical | identical |