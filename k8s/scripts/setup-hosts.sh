#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[hosts]${NC} $1"; }
ok()  { echo -e "${GREEN}✅${NC} $1"; }

MINIKUBE_IP=$(minikube ip)
HOSTNAME="rag.local"
HOSTS_FILE="/etc/hosts"

log "Minikube IP: $MINIKUBE_IP"

# Remove old entry if exists
sed -i.bak "/$HOSTNAME/d" $HOSTS_FILE

# Add new entry
echo "$MINIKUBE_IP $HOSTNAME" >> $HOSTS_FILE

ok "Added to /etc/hosts: $MINIKUBE_IP $HOSTNAME"
log "Verify with: cat /etc/hosts | grep rag.local"
echo ""
log "Access URLs:"
echo "  API     : http://rag.local"
echo "  Docs    : http://rag.local/docs"
echo "  Flower  : http://rag.local/flower"
echo "  Grafana : http://rag.local/grafana"
echo "  Metrics : http://rag.local/prometheus"