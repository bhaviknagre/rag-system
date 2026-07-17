# Security

## Dependency vulnerabilities

`requirements.txt` is audited with [`pip-audit`](https://pypi.org/project/pip-audit/)
against the PyPI Advisory Database. As of the last audit, the pinned
versions resolve the overwhelming majority of known CVEs in this
dependency tree. A handful remain open because fixing them requires a
breaking major-version migration (see below) rather than a version bump —
they're tracked here deliberately instead of silently ignored.

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

### Patched in this revision

| Package | Was | Now | Notes |
|---|---|---|---|
| `fastapi` | 0.115.6 | 0.139.0 | Needed to unlock a patched `starlette` |
| `starlette` | 0.41.3 (transitive) | 1.3.1 | Pulled in via `fastapi`; explicitly pinned so the resolver can't quietly settle on an old build |
| `prometheus-fastapi-instrumentator` | 7.0.0 | 8.0.2 | 7.x hard-capped `starlette<1.0`; 8.x lifts the cap. API used by this project (`Instrumentator(...).instrument().expose()`) is unchanged |
| `pydantic` / `pydantic-settings` | 2.9.2 / 2.6.1 | 2.13.4 / 2.12.0 | Required by newer `langchain-community` |
| `langchain` / `langchain-core` / `langchain-community` / `langchain-text-splitters` | 0.3.13 / 0.3.28 / 0.3.13 / 0.3.4 | 0.3.30 / 0.3.86 / 0.3.31 / 0.3.11 | Latest release on the 0.3.x line — see "Known open items" for what this does *not* fix |
| `aiohttp` | 3.9.5 (transitive) | 3.14.1 | Was capped by `langchain-pinecone==0.2.0`'s `aiohttp<3.10`; fixed by bumping that package instead |
| `python-multipart` | 0.0.20 | 0.0.32 | |
| `requests` | 2.32.3 | 2.33.0 | |
| `python-dotenv` | 1.0.1 | 1.2.2 | |
| `pypdf` | 5.1.0 | 6.14.2 | Major version bump; usage in this codebase (`PdfReader(path).pages[i].extract_text()`) is the stable core API and unaffected |
| `unstructured` | 0.16.11 | 0.18.18 | Not imported directly anywhere in `src/` or `api/` — installed as a `langchain-community` loader dependency only |
| `certifi` | 2024.12.14 | 2026.6.17 | CA bundle refresh |
| `pinecone-client` | 5.0.1 | — (replaced) | See below — this was a real bug, not just a version bump |

### A real bug found during remediation, not just a CVE

`pinecone-client==5.0.1` (the deprecated package name) and `pinecone`
(the current package name, pulled in transitively once `langchain-pinecone`
is upgraded) **both install into the same `pinecone/` top-level module**.
Having both pinned means whichever installs last silently overwrites the
other's files — a real, reproducible failure mode, not a hypothetical one
(confirmed by installing both into a clean venv and inspecting
`site-packages`). Fixed by dropping `pinecone-client` and pinning `pinecone==7.3.0`
directly; `from pinecone import Pinecone, ServerlessSpec` in
`src/vectorstore/store.py` is unchanged and works identically against the
new package.

### Known open items (not fixed — by design)

!!! warning "Fixing these requires a langchain 0.3 → 1.x migration"
    A few CVEs in `langchain-core`, `langchain`, and `langchain-text-splitters`
    have no patched release on the 0.3.x line — the fix landed only in the
    1.x series. Upgrading there is not just a version bump: `langchain-chroma`,
    `langchain-mongodb`, `langchain-huggingface`, and `langchain-experimental`
    would all need matching major-version upgrades, several of which change
    import paths and constructor signatures used in
    `src/ingestion/chunker.py`, `src/embedings/embedder.py`, and
    `src/vectorstore/store.py`. That's a real code migration, not a
    dependency-file edit, so it was deliberately deferred rather than rushed
    through as part of a version bump. Track it as a follow-up task.

| Package | CVE / advisory | Fixed only in | Current exposure |
|---|---|---|---|
| `langchain-core` | path traversal in prompt loading | `>=1.2.22` | Local-only prompt templates are hardcoded in `src/generation/generator.py`, not loaded from untrusted paths — reduces but does not eliminate exposure |
| `langchain-core` | (2 further advisories) | `>=1.2.11` / `>=1.3.3` | Same as above |
| `langchain` | serialization advisory | `>=1.3.9` | Not directly imported by this project's code (only `langchain_core`, `langchain_text_splitters`, `langchain_experimental`, `langchain_huggingface`, and the `langchain_*` vector store integrations are imported) |
| `langchain-text-splitters` | advisory | `>=1.1.2` | `RecursiveCharacterTextSplitter` usage in `chunker.py` is the stable base API |
| `transformers` | multiple advisories | `>=4.53.0` / `5.x` for a few | Capped by `sentence-transformers==3.3.1`; bumping either changes embedding output and risks invalidating existing vector store data. Left untouched deliberately — see [Embeddings](../components/embeddings.md) |
| `diskcache` | advisory | none published yet | Transitive via `dvc`; nothing to upgrade to |

### ChromaDB HTTP server RCE — not applicable

!!! danger "CVE-2026-45829 — ChromaDB Python server (pre-auth RCE)"
    Affects ChromaDB's HTTP server mode only, via a malicious HuggingFace
    model reference in `create_collection`.

    **This deployment is not affected.** `src/vectorstore/store.py` uses
    `chromadb.PersistentClient()` — local, in-process, file-backed. The
    HTTP server is never started, so there is no network-reachable attack
    surface for this CVE. Confirm this stays true before ever switching to
    `chromadb.HttpClient()`.

---

## Incident: real credentials were committed in `k8s/secrets/secrets.yaml`

A previous commit (`added the K8s manifest to the system`) checked in
`k8s/secrets/secrets.yaml` with **real base64-encoded values** — a live
Pinecone API key and a MongoDB Atlas URI with embedded username/password —
instead of the placeholders the file's own comments described. Since this
repo's remote is a public GitHub repository, those values were exposed
publicly from the moment that commit was pushed.

The file has been reset to placeholder values (`base64("your-key-here")`)
and `API_KEY` was added alongside `PINECONE_API_KEY` / `MONGODB_ATLAS_URI`.
**Rotating the real Pinecone key and MongoDB Atlas password is the
responsibility of whoever owns those accounts** — treat both as
compromised regardless of the file fix, since they remain visible in git
history until/unless it is rewritten (`git filter-repo` + force-push),
which was deliberately not done here to avoid breaking clones/forks
without a deliberate decision to do so.

**Going forward:** never put a real value directly in a file destined for
`kubectl apply -f` and tracked in git. Prefer `kubectl create secret
generic ... --from-literal=` run by hand or CI against the cluster, with
the committed YAML holding only placeholders as documented.

---

## Secrets — do not default them in code

A previous revision of `src/config.py` shipped a **hardcoded MongoDB Atlas
connection string with embedded credentials** as the default value for
`mongodb_atlas_uri`. That default has been removed — the field now
defaults to `""`, matching the pattern already used for `pinecone_api_key`,
and `src/vectorstore/store.py` raises a clear `ValueError` if the MongoDB
backend is selected without `MONGODB_ATLAS_URI` set.

**If that credential was ever real, rotate it in MongoDB Atlas regardless
of anything else in this document** — a credential that has been committed
to git history should be treated as compromised even after the file is
fixed, since the old commits still contain it unless history is rewritten.

```bash
# Always use .env (gitignored) — never hardcode defaults in src/config.py
cp .env.example .env

# In Kubernetes — use Secrets, never ConfigMap for sensitive values
kubectl get secret rag-secrets -n rag-system -o jsonpath='{.data.PINECONE_API_KEY}' \
  | base64 --decode
```

---

## Fixed: MongoDB client no longer built at import time

`src/vectorstore/store.py` used to construct a module-level `MongoClient`
unconditionally on import — meaning any deployment that only uses the
default `chroma` backend still paid the cost (and risk) of a MongoDB
connection attempt at startup, and an empty/invalid `MONGODB_ATLAS_URI`
would crash the entire API process before it could serve a single request.
Confirmed directly: `MongoClient("")` raises `ConfigurationError: Empty
host` at construction, not at first use. The client is now built lazily,
only when the `mongodb` provider is actually selected.

---

## Authentication

`api/auth.py` implements a shared-secret `X-API-Key` header check via a
FastAPI dependency (`require_api_key`), applied to `POST /ingest`,
`POST /upload`, `POST /ask`, `GET /jobs/{job_id}`, and
`DELETE /jobs/{job_id}/cancel` in `api/main.py`. The expected key comes
from the `API_KEY` environment variable.

If `API_KEY` is unset, auth is skipped and a warning is logged once —
this is deliberate, so local/dev usage (and the Quickstart flow) isn't
broken by a hard requirement, but it means **an unset `API_KEY` is an
open API**. Set `API_KEY` before exposing this stack beyond a trusted
network:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# put the result in .env / k8s Secret as API_KEY
```

`/health`, `/providers`, `/strategies`, `/metrics`, `/`, and the web UI
(`/rag-system`) are intentionally left ungated — none of them mutate
state or run the LLM. The static web UI (`static/index.html`) has an
API-key input field in the header that stores the value in
`localStorage` and attaches it as `X-API-Key` on every protected call.

## Nginx rate limiting

Rate limits are applied per endpoint at the Nginx layer:

| Endpoint | Limit | Burst |
|---|---|---|
| `/ask` | 10 req/s per IP | 20 |
| `/ingest` | 2 req/s per IP | 5 |
| `/upload` | 2 req/s per IP | 5 |
| `/` (general) | 30 req/s per IP | 20 |

Exceeds return HTTP 429 with a JSON error body.

## CORS

`api/main.py` currently sets `allow_origins=["*"]` with credentials-free
CORS. Fine for local development; scope this to specific origins before
any public deployment.
