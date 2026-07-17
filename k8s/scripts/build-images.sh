#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[build]${NC} $1"; }
ok()  { echo -e "${GREEN}✅${NC} $1"; }

log "Pointing Docker CLI to Minikube's Docker daemon..."
eval $(minikube docker-env)

log "Building rag-api image inside Minikube..."
docker build -t rag-api:latest .
ok "rag-api:latest built"

log "Verifying image is visible to Minikube..."
minikube image ls | grep rag-api
ok "Image visible to Minikube"

echo ""
log "Done. Deploy with: bash k8s/scripts/deploy.sh"