# Quickstart

## Local (Python)

```bash
# 1. Clone
git clone https://github.com/your-username/rag-system.git
cd rag-system

# 2. Virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — add Pinecone key + MongoDB URI if using those backends

# 5. Start Redis
docker run -d -p 6379:6379 redis:7.2-alpine

# 6. Start Ollama (separate terminal)
ollama serve
ollama pull llama3.2:1b

# 7. Start Celery worker (separate terminal)
celery -A src.worker.celery_app worker --loglevel=info

# 8. Add documents
cp your_docs/*.pdf data/raw/

# 9. Run DVC pipeline
dvc repro

# 10. Start API
uvicorn api.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for Swagger UI.

## Docker Compose

```bash
cp .env.example .env   # fill in secrets
docker compose up --build -d
bash scripts/healthcheck.sh
```

| Service | URL |
|---|---|
| API | http://localhost |
| UI | http://localhost/ui |
| Flower | http://localhost:5555 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

## Kubernetes (Minikube)

```bash
# Prerequisites
brew install minikube kubectl helm
minikube start --driver=docker --cpus=4 --memory=6144

# Enable addons
minikube addons enable ingress
minikube addons enable metrics-server

# Deploy
bash k8s/scripts/build-images.sh
bash k8s/scripts/deploy.sh
sudo bash k8s/scripts/setup-hosts.sh
minikube tunnel   # keep running
```

Open **http://rag.local** — everything routes from there.

## Your first query

```bash
# 1. Ingest a document
curl -X POST http://localhost/ingest \
  -H "Content-Type: application/json" \
  -d '{"provider": "chroma", "strategy": "recursive", "reset": true}'

# 2. Check job status
curl http://localhost/jobs/<job_id>

# 3. Ask a question
curl -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "provider": "chroma"}'
```