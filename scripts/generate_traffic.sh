#!/bin/bash
# Generates real traffic so Prometheus has data to show in Grafana

GREEN='\033[0;32m'
NC='\033[0m'

echo "Generating traffic against RAG API..."
echo ""

# Health checks
echo "1. Health checks (10x)..."
for i in {1..10}; do
  curl -s http://localhost/health > /dev/null
done
echo -e "${GREEN}done${NC}"

# Ask questions
echo "2. Ask questions (8x)..."
QUESTIONS=(
  "What is this document about?"
  "What are the main topics?"
  "What tools are mentioned?"
  "Who are the key people involved?"
  "What are the conclusions?"
  "Summarize the document"
  "What technologies are used?"
  "What are the key findings?"
)

for q in "${QUESTIONS[@]}"; do
  curl -s -X POST http://localhost/ask \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"$q\", \"provider\": \"chroma\"}" \
    > /dev/null
  sleep 0.5
done
echo -e "${GREEN}done${NC}"

# Ingest jobs
echo "3. Ingest jobs (3x)..."
for i in {1..3}; do
  JOB=$(curl -s -X POST http://localhost/ingest \
    -H "Content-Type: application/json" \
    -d '{"provider": "chroma", "strategy": "recursive", "reset": false}')
  JOB_ID=$(echo $JOB | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)
  echo "  Job queued: $JOB_ID"
  sleep 2
done
echo -e "${GREEN}done${NC}"

# Providers check
echo "4. Provider checks (3x)..."
for i in {1..3}; do
  curl -s http://localhost/providers > /dev/null
done
echo -e "${GREEN}done${NC}"

echo ""
echo "Traffic generation complete."
echo "Wait 15 seconds then check:"
echo "  Prometheus : http://localhost:9090"
echo "  Grafana    : http://localhost:3000"
echo "  Flower     : http://localhost:5555"