# Generation

**File:** `src/generation/generator.py`

Generates a grounded answer from retrieved context using
a local LLM served by Ollama. No API key required.

---

## Model

| Property | Value |
|---|---|
| Model | `llama3.2:1b` |
| Provider | Ollama (local) |
| Parameters | 1 billion |
| Context window | 4096 tokens |
| Quantization | Q4_K_M |
| Inference | CPU (no GPU required) |
| RAM required | ~800MB |
| Latency | 5-30s on CPU |
| Cost | $0 |

---

## Prompt template

You are a helpful assistant answering questions based ONLY
on the provided context.
If the answer is not contained in the context, say:
"I don't have enough information in the provided documents to answer that."
Do not make up information.
Context:
{context}
Question: {question}

Answer:

The strict prompt prevents hallucination — the model is explicitly
instructed not to use knowledge outside the provided context.

---

## Model comparison

| Model | Params | RAM | CPU Latency | Quality | Cost |
|---|---|---|---|---|---|
| llama3.2:1b (default) | 1B | ~800MB | 5-30s | Acceptable | $0 |
| llama3.2:3b | 3B | ~2GB | 15-60s | Good | $0 |
| mistral:7b | 7B | ~4GB | 30-90s | Very good | $0 |
| GPT-4o-mini | ~8B | API | 1-3s | Excellent | $0.15/1M tokens |

### Switching models

Change in `.env` — no code change needed:

```env
LLM_MODEL=llama3.2:3b
```

Then pull the new model:
```bash
# Local
ollama pull llama3.2:3b

# In Docker/K8s
docker exec rag-ollama ollama pull llama3.2:3b
# or
kubectl exec -n rag-system ollama-0 -- ollama pull llama3.2:3b
```

---

## Silent failures in production

!!! warning "Where the LLM fails silently"

    | Failure | How it manifests | Fix |
    |---|---|---|
    | Context overflow | Answer truncated or incoherent | Reduce `TOP_K` or `CHUNK_SIZE` |
    | Numerical reasoning | "15% of €1.2M" answered incorrectly | Use GPT-4o-mini for maths |
    | Multi-hop reasoning | "Who approved the budget?" fails | Increase TOP_K, use re-ranking |
    | Contradicting context | Model picks one chunk arbitrarily | Flag conflicts in prompt |
    | Prompt injection | Malicious doc content overrides instructions | Sanitize doc content on ingest |

---

## Ollama API

The generator calls Ollama's local REST API:

```python
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": settings.llm_model,
        "prompt": prompt,
        "stream": False
    },
    timeout=120
)
```

If Ollama is unreachable, the generator returns a graceful error message
(not an exception) so the API response still has a valid JSON structure.