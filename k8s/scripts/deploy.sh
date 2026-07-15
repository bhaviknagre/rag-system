#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${BLUE}[k8s]${NC} $1"; }
ok()   { echo -e "${GREEN}✅${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $1"; }

echo ""
echo "══════════════════════════════════════"
echo "   RAG System — Full K8s Deploy"
echo "══════════════════════════════════════"
echo ""

# Phase 1
log "Phase 1: Namespace + Config + Secrets"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap/configmap.yaml
kubectl apply -f k8s/secrets/secrets.yaml
ok "Phase 1 done"

# Phase 2
log "Phase 2: Redis"
kubectl apply -f k8s/redis/deployment.yaml
kubectl apply -f k8s/redis/service.yaml
kubectl rollout status deployment/redis -n rag-system --timeout=120s
ok "Phase 2 done"

# Phase 3
log "Phase 3: Ollama (model pull may take 5 min first time)"
kubectl apply -f k8s/ollama/statefulset.yaml
kubectl apply -f k8s/ollama/service.yaml
kubectl rollout status statefulset/ollama -n rag-system --timeout=600s
ok "Phase 3 done"

# Phase 4
log "Phase 4: API"
bash k8s/scripts/build-images.sh
kubectl apply -f k8s/api/deployment.yaml
kubectl apply -f k8s/api/service.yaml
kubectl apply -f k8s/api/hpa.yaml
kubectl rollout status deployment/rag-api -n rag-system --timeout=180s
ok "Phase 4 done"

# Phase 5
log "Phase 5: Worker + KEDA"
kubectl apply -f k8s/worker/deployment.yaml
kubectl apply -f k8s/worker/keda-scaledobject.yaml
ok "Phase 5 done"

# Phase 6
log "Phase 6: Flower + Monitoring"
kubectl apply -f k8s/flower/deployment.yaml
kubectl apply -f k8s/flower/service.yaml
kubectl apply -f k8s/monitoring/servicemonitor.yaml
kubectl apply -f k8s/monitoring/prometheus-rules.yaml
kubectl apply -f k8s/monitoring/grafana-dashboard-configmap.yaml
ok "Phase 6 done"

# Phase 7
log "Phase 7: Ingress"
kubectl apply -f k8s/ingress/grafan-config.yaml
kubectl apply -f k8s/ingress/ingress.yaml
ok "Phase 7 done"

echo ""
echo "══════════════════════════════════════"
ok "Full deployment complete"
echo ""
log "Setting up rag.local hostname..."
warn "Next step needs sudo:"
echo "  sudo bash k8s/scripts/setup-hosts.sh"
echo ""
log "Access URLs (after running setup-hosts.sh):"
echo "  API      : http://rag.local"
echo "  Docs     : http://rag.local/docs"
echo "  Flower   : http://rag.local/flower"
echo "  Grafana  : http://rag.local/grafana  (admin/ragadmin)"
echo "  Prom     : http://rag.local/prometheus"
echo "══════════════════════════════════════"