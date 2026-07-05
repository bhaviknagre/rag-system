set -e

# Colours for log prefixes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Starting RAG System (local)...${NC}"

# ── 1. Redis ─────────────────────────────────
echo -e "${YELLOW}[redis]${NC} Starting Redis on port 6379..."
docker run -d \
  --name rag-redis-local \
  -p 6379:6379 \
  redis:7.2-alpine \
  redis-server --appendonly yes \
  2>/dev/null || echo -e "${YELLOW}[redis]${NC} Already running"

# Wait for Redis to be ready
until docker exec rag-redis-local redis-cli ping 2>/dev/null | grep -q PONG; do
  echo -e "${YELLOW}[redis]${NC} Waiting..."
  sleep 1
done
echo -e "${YELLOW}[redis]${NC} Ready"

# ── 2. Ollama ────────────────────────────────
echo -e "${BLUE}[ollama]${NC} Checking Ollama..."
if ! pgrep -x "ollama" > /dev/null; then
  echo -e "${BLUE}[ollama]${NC} Starting ollama serve..."
  ollama serve &>/dev/null &
  sleep 2
fi

# Check if model is pulled
if ! ollama list 2>/dev/null | grep -q "llama3.2:1b"; then
  echo -e "${BLUE}[ollama]${NC} Pulling llama3.2:1b (one-time ~1.3GB download)..."
  ollama pull llama3.2:1b
fi
echo -e "${BLUE}[ollama]${NC} Ready"

# ── 3. Celery worker ─────────────────────────
echo -e "${RED}[worker]${NC} Starting Celery worker..."
celery -A src.worker.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --logfile=data/processed/celery.log &
WORKER_PID=$!
echo -e "${RED}[worker]${NC} PID=$WORKER_PID | logs → data/processed/celery.log"

# ── 4. Flower (optional monitoring) ──────────
echo -e "${RED}[flower]${NC} Starting Flower on http://localhost:5555..."
celery -A src.worker.celery_app flower \
  --port=5555 \
  --logfile=data/processed/flower.log &
FLOWER_PID=$!

# ── 5. FastAPI ───────────────────────────────
echo -e "${GREEN}[api]${NC} Starting FastAPI on http://localhost:8000..."
echo -e "${GREEN}[api]${NC} Swagger UI → http://localhost:8000/docs"
echo -e "${GREEN}[api]${NC} Flower UI  → http://localhost:5555"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop all services"
echo ""

# Trap Ctrl+C to clean up background processes
trap "echo ''; echo 'Stopping...'; kill $WORKER_PID $FLOWER_PID 2>/dev/null; docker stop rag-redis-local 2>/dev/null; exit 0" INT

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000