# Auto-Scaling

Two different scaling strategies are used intentionally for
different components.

---

## API — HorizontalPodAutoscaler (CPU + Memory)

**Why HPA for API?** API pods are stateless HTTP servers.
CPU and memory are good proxies for request load.

```yaml
minReplicas: 2
maxReplicas: 10
metrics:
  - cpu:    averageUtilization: 60
  - memory: averageUtilization: 70
```

### Scale-up behavior

Current: 2 pods @ avg 80% CPU (target 60%)
Scale factor = 80/60 = 1.33
New replicas = ceil(2 × 1.33) = 3

Up to **4 pods added per 60 seconds** (fast response to spikes).
`stabilizationWindowSeconds: 30` prevents over-caution.

### Scale-down behavior

Conservative — waits **5 minutes** before removing pods.
Removes **1 pod per 60 seconds** at minimum.
Prevents thrashing if load oscillates.

---

## Workers — KEDA ScaledObject (Queue Depth)

**Why KEDA for workers?** Workers are idle between jobs.
CPU stays at 0% even with 10 jobs queued — HPA would never scale.

```yaml
triggers:
  - type: redis
    metadata:
      listName: celery
      listLength: "2"          # 1 worker per 2 queued jobs
      pollingInterval: 10      # check every 10 seconds
      cooldownPeriod: 60       # wait 60s before scale-to-zero
```

### Why queue depth beats CPU

Scenario: 10 jobs arrive in Redis
CPU-based HPA:
Workers idle → CPU = 0% → HPA sees nothing → does NOT scale
Worker picks up job 1 → CPU spikes → HPA scales → 9 jobs wait
KEDA queue-depth:
10 jobs arrive → queue depth = 10 → KEDA detects in ≤10s
Scales to 5 workers immediately → jobs processed in parallel

Queue depth is a **leading indicator**. CPU is a **lagging indicator**.

### Scale-to-zero

When the queue empties, KEDA scales workers to 0 after the cooldown
period (60 seconds). This saves significant memory on Minikube
(each worker pod uses ~500MB-2GB).

---

## Manual scaling

```bash
# Scale API manually (overrides HPA temporarily)
kubectl scale deployment/rag-api --replicas=5 -n rag-system

# HPA will regain control on next evaluation cycle (30s)

# Scale using the helper script
bash k8s/scripts/scale.sh up      # 3 API + 3 workers
bash k8s/scripts/scale.sh down    # 1 API + 0 workers
bash k8s/scripts/scale.sh status  # show current counts
```

---

## Load testing to trigger scaling

```bash
# Submit 10 jobs rapidly — watch KEDA spin up workers
for i in {1..10}; do
  curl -s -X POST http://rag.local/ingest \
    -H "Content-Type: application/json" \
    -d '{"provider": "chroma", "strategy": "recursive"}' &
done
wait

# Watch workers appear
kubectl get pods -n rag-system -w | grep worker

# Check KEDA ScaledObject status
kubectl describe scaledobject rag-worker-scaledobject -n rag-system
```