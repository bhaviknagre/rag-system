# Security

## Known Vulnerabilities & Status

!!! danger "CVE-2025-68664 — langchain-core (CVSS 9.3) — PATCHED"
    **LangGrinch serialization injection.** Affected all langchain-core
    versions before `0.3.81`. Could leak API keys and env vars via prompt
    injection, potential RCE via Jinja2.

    **Our fix:** Upgraded to `langchain-core==1.4.9` ✅

!!! danger "CVE-2026-34070 — langchain-core (CVSS 7.5) — PATCHED"
    **Path traversal in prompt loading.** Fixed in `langchain-core>=1.2.22`.

    **Our fix:** Upgraded to `langchain-core==1.4.9` ✅

!!! warning "CVE-2026-45829 — ChromaDB Python server (pre-auth RCE) — UNPATCHED"
    **Affects ChromaDB HTTP server mode only.** Pre-authentication RCE via
    malicious HuggingFace model in `create_collection`.

    **Our mitigation:** We use `chromadb.PersistentClient()` (local file mode).
    The HTTP server is **never started**. Network exposure is zero. ✅

    Monitor: https://github.com/chroma-core/chroma/issues/6717

## Checking for vulnerabilities

```bash
# Install pip-audit
pip install pip-audit

# Scan your installed packages
pip-audit

# Scan requirements.txt without installing
pip-audit -r requirements.txt
```

## Environment variables — never commit secrets

```bash
# Always use .env (gitignored)
cp .env.example .env

# In Kubernetes — use Secrets, never ConfigMap for sensitive values
kubectl get secret rag-secrets -n rag-system -o jsonpath='{.data.PINECONE_API_KEY}' \
  | base64 --decode
```

## Nginx rate limiting

Rate limits are applied per endpoint at the Nginx layer:

| Endpoint | Limit | Burst |
|---|---|---|
| `/ask` | 10 req/s per IP | 20 |
| `/ingest` | 2 req/s per IP | 5 |
| `/upload` | 2 req/s per IP | 5 |
| `/` (general) | 30 req/s per IP | 20 |

Exceeds return HTTP 429 with JSON error body.