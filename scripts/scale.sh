set -e

ACTION=${1:-status}

case $ACTION in
  up)
    echo "Scaling UP: 3 API instances + 3 Celery workers"
    docker compose up -d --scale rag-api=3 --scale rag-worker=3 --no-recreate
    echo ""
    echo "Services running:"
    docker compose ps | grep -E "rag-api|rag-worker"
    echo ""
    echo "Nginx is load balancing across all API instances."
    echo "Access at http://localhost"
    ;;

  down)
    echo "Scaling DOWN: 1 API instance + 1 Celery worker"
    docker compose up -d --scale rag-api=1 --scale rag-worker=1 --no-recreate
    echo ""
    docker compose ps | grep -E "rag-api|rag-worker"
    ;;

  status)
    echo "Current instance counts:"
    echo ""
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    API_COUNT=$(docker compose ps rag-api 2>/dev/null | grep -c "Up" || echo 0)
    WORKER_COUNT=$(docker compose ps rag-worker 2>/dev/null | grep -c "Up" || echo 0)
    echo "  API instances    : $API_COUNT"
    echo "  Worker instances : $WORKER_COUNT"
    ;;

  *)
    echo "Usage: $0 [up|down|status]"
    exit 1
    ;;
esac