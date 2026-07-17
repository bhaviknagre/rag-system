#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[rollout]${NC} $1"; }
ok()  { echo -e "${GREEN}✅${NC} $1"; }

VERSION=${1:-latest}

log "Starting zero-downtime rollout (version: $VERSION)..."

# Step 1: Build new image inside Minikube
log "Building image inside Minikube..."
eval $(minikube docker-env)
docker build -t rag-api:$VERSION .
ok "Image built: rag-api:$VERSION"

# Step 2: Update image tag in deployments
log "Updating API deployment..."
kubectl set image deployment/rag-api \
  rag-api=rag-api:$VERSION \
  -n rag-system

log "Updating Worker deployment..."
kubectl set image deployment/rag-worker \
  rag-worker=rag-api:$VERSION \
  -n rag-system

log "Updating Flower deployment..."
kubectl set image deployment/flower \
  flower=rag-api:$VERSION \
  -n rag-system

# Step 3: Wait for rollouts
log "Waiting for API rollout..."
kubectl rollout status deployment/rag-api -n rag-system --timeout=120s
ok "API rolled out"

log "Waiting for Flower rollout..."
kubectl rollout status deployment/flower -n rag-system --timeout=120s
ok "Flower rolled out"

log "Worker is managed by KEDA — will use new image on next scale event"
ok "Rollout complete"

# Step 4: Verify
echo ""
log "Current state:"
kubectl get pods -n rag-system
echo ""
log "Access: http://rag.local"