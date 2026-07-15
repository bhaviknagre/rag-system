# 7-Phase Build

Each phase was applied and verified before moving to the next.

---

## Phase 1 — Namespace + Config + Secrets

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap/configmap.yaml
kubectl apply -f k8s/secrets/secrets.yaml
```

**Concepts:** Namespaces, ConfigMaps, Opaque Secrets, base64 encoding

**Key decision:** All 16 env vars in ConfigMap.
Sensitive values (API keys, DB URIs) in Opaque Secret.
Nothing hardcoded in any manifest.

---

## Phase 2 — Redis

```bash
kubectl apply -f k8s/redis/deployment.yaml
kubectl apply -f k8s/redis/service.yaml
```

**Concepts:** Deployment, PersistentVolumeClaim, ClusterIP Service,
liveness probe, readiness probe

**Key decision:** PVC ensures job results survive pod restarts.
Redis crash does not lose queued work.

Verify:
```bash
kubectl exec -n rag-system \
  $(kubectl get pod -n rag-system -l app=redis -o jsonpath='{.items[0].metadata.name}') \
  -- redis-cli ping
# Expected: PONG
```

---

## Phase 3 — Ollama StatefulSet

```bash
kubectl apply -f k8s/ollama/statefulset.yaml
kubectl apply -f k8s/ollama/service.yaml
```

**Concepts:** StatefulSet, `volumeClaimTemplates`, Headless Service,
init containers, stable pod identity

**Key decision:** StatefulSet (not Deployment) because the 5Gi model
volume must be permanently bound to `ollama-0`. A Deployment would
re-download the 1.3GB model on every pod reschedule.

Verify:
```bash
kubectl exec -n rag-system ollama-0 -- ollama list
# Expected: llama3.2:1b listed
```

---

## Phase 4 — API Deployment + HPA

```bash
kubectl apply -f k8s/api/deployment.yaml
kubectl apply -f k8s/api/service.yaml
kubectl apply -f k8s/api/hpa.yaml
```

**Concepts:** Deployment, RollingUpdate, three probe types,
HorizontalPodAutoscaler, CPU + memory scaling

**Key decisions:**

- `startupProbe failureThreshold=12 × 5s` gives 60s grace on cold start
- `readinessProbe` gates traffic — pods only receive requests when truly ready
- HPA scales on both CPU (60%) AND memory (70%) simultaneously
- `scaleDown.stabilizationWindowSeconds=300` prevents thrashing

Verify:
```bash
kubectl get hpa -n rag-system
# Expected: TARGETS showing cpu% / memory%
```

---

## Phase 5 — Worker + KEDA

```bash
kubectl apply -f k8s/worker/deployment.yaml
kubectl apply -f k8s/worker/keda-scaledobject.yaml
```

**Concepts:** KEDA ScaledObject, queue-based autoscaling,
scale-to-zero, event-driven scaling

**Key decision:** KEDA over CPU-based HPA because queue depth is a
**leading indicator** of demand. CPU only rises after a worker starts
processing — KEDA scales before CPU ever rises.

| Queue depth | Workers | Formula |
|---|---|---|
| 0 | 0 | scale-to-zero |
| 2 | 1 | ceil(2/2) = 1 |
| 6 | 3 | ceil(6/2) = 3 |
| 20+ | 10 | maxReplicaCount cap |

Verify:
```bash
kubectl get scaledobject -n rag-system
# Expected: READY=True, ACTIVE=False (when queue empty)
```

---

## Phase 6 — Flower + Monitoring

```bash
kubectl apply -f k8s/flower/deployment.yaml
kubectl apply -f k8s/flower/service.yaml
kubectl apply -f k8s/monitoring/servicemonitor.yaml
kubectl apply -f k8s/monitoring/prometheus-rules.yaml
kubectl apply -f k8s/monitoring/grafana-dashboard-configmap.yaml
```

**Concepts:** ServiceMonitor CRD, PrometheusRule CRD, Grafana
sidecar auto-provisioning, Prometheus Operator

**Key decision:** ServiceMonitor replaces manual `prometheus.yml` editing.
The Prometheus Operator watches for `ServiceMonitor` resources and
automatically configures Prometheus scrape targets.

---

## Phase 7 — Ingress

```bash
kubectl apply -f k8s/ingress/ingress.yaml
kubectl patch deployment prometheus-stack-grafana -n monitoring ...
sudo bash k8s/scripts/setup-hosts.sh
minikube tunnel
```

**Concepts:** Nginx Ingress, path-based routing, `rewrite-target`,
session cookie affinity, `minikube tunnel`

**Key decision:** Three separate Ingress resources (one per namespace)
because Kubernetes Ingress resources are namespace-scoped.
Grafana uses cookie affinity to prevent session loss when
requests route to different Grafana pods.