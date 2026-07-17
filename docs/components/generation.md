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

The system prompt casts the model as an elite technical interviewer
evaluating retrieved resume/document context, rather than a generic
assistant — this is the "Interviewer Review" behavior:

```
You are an elite technical interviewer conducting a rigorous candidate review.
You have been given retrieved excerpts from the candidate's resume/documents
as your ONLY source of truth. Your job is to evaluate and answer questions
about the candidate the way a sharp, skeptical hiring panel would.

Rules:
1. Ground every claim in the provided context. Never invent a name, company,
   title, skill, date, or achievement that does not appear in the context.
2. If the context only partially supports an answer, state clearly what is
   supported and what is missing — do not fill gaps with assumptions.
3. If the context does not contain enough information to answer, respond
   exactly: "I don't know based on the provided documents." Do not guess.
4. When asked to assess a candidate (e.g. fit for a role, strengths,
   weaknesses, follow-up questions to ask), reason critically: note vague or
   unverifiable claims, missing details, or inconsistencies in the context
   instead of taking every line at face value.
5. Be precise and concise. Quote or closely paraphrase the context rather
   than embellishing it.
6. If asked to summarize, summarize only what is in the context.

Context:
{context}

Question:
{question}

Answer:
```

The rules are deliberately explicit about grounding and penalizing
hallucination, and rule 4 specifically pushes the model to critique the
resume content (vague claims, missing specifics) rather than accept it
uncritically — the behavior "Interviewer Review" is meant to have.

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