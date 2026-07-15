# Document Ingestion

**File:** `src/ingestion/loader.py` + `src/ingestion/chunker.py`

The ingestion layer handles two concerns:
loading raw documents into text, and splitting that text into
chunks suitable for embedding.

---

## Document Loader

### Supported Formats

| Format | Library | Extraction Method | Known Limitation |
|---|---|---|---|
| `.txt` | Python built-in | `read_text()` UTF-8 | None — most reliable |
| `.pdf` | pypdf 5.1.0 | `page.extract_text()` per page | Scanned PDFs return empty (no OCR) |
| `.docx` | python-docx 1.1.2 | paragraph join | Tables inside DOCX ignored |

### Usage

```python
from src.ingestion.loader import load_documents_from_directory

docs = load_documents_from_directory("data/raw")
# Returns: [{"doc_id": "file.pdf", "text": "...", "source": "data/raw/file.pdf"}]
```

### How it works

```python
def load_document(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":   return load_txt(file_path)
    elif suffix == ".pdf": return load_pdf(file_path)
    elif suffix == ".docx":return load_docx(file_path)
```

Empty documents are skipped with a warning. Errors per file are caught
and logged — one bad file does not abort the entire ingestion.

---

## Chunker

### Three Strategies

=== "Recursive"

    Structure-aware splitting using LangChain's
    `RecursiveCharacterTextSplitter`.

    **Separator hierarchy:**

    1. `\n\n` — paragraph boundary
    2. `\n` — line break
    3. `. ` — sentence boundary
    4. ` ` — word boundary
    5. `""` — character fallback

    **Config:**
```env
    CHUNK_SIZE=500      # words per chunk
    CHUNK_OVERLAP=50    # overlap words between chunks
```

    **Output:** 30-50 chunks per average document. Deterministic.

=== "Semantic"

    Embedding-based splitting using LangChain's `SemanticChunker`.
    Splits at cosine distance spikes between adjacent sentences.

```python
    splitter = SemanticChunker(
        embeddings=get_embeddings(),
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90   # split at top 10% of distance jumps
    )
```

    !!! warning "Performance"
        Semantic chunking runs the embedding model on every sentence
        during chunking. Expect 10-20x slower than recursive.

=== "Sentence Window"

    Per-sentence chunking with surrounding context in metadata.

```python
    Document(
        page_content=sentence,          # the chunk itself
        metadata={
            "window_context": "...",    # surrounding sentences
            "sentence_index": i,
            "total_sentences": total
        }
    )
```

    The `window_context` is injected into the LLM prompt at query time
    for richer answers even though retrieval matched on a single sentence.

### Unified Output Schema

All three strategies produce the same chunk dict:

```python
{
    "chunk_id":  "filename.pdf_recursive_chunk_0",
    "doc_id":    "filename.pdf",
    "source":    "data/raw/filename.pdf",
    "text":      "The actual chunk text...",
    "metadata": {
        "strategy":      "recursive",
        "chunk_index":   0,
        "window_context": ""   # populated by sentence_window only
    }
}
```

### Adding a new document

```bash
# Drop file in data/raw/
cp my_doc.pdf data/raw/

# Via API (async)
curl -X POST http://localhost/upload \
  -F "file=@my_doc.pdf" \
  -F "provider=chroma" \
  -F "strategy=recursive"

# Via DVC (synchronous, tracked)
dvc add data/raw
dvc repro
```