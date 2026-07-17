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
| `.pdf` | pdfplumber (primary) + pypdf (fallback) | `page.extract_text(layout=True)` per page, falling back to pypdf if pdfplumber raises or returns nothing | Scanned PDFs return empty (no OCR) |
| `.docx` | python-docx 1.1.2 | paragraph join | Tables inside DOCX ignored |

### PDF extraction: pdfplumber-first, pypdf fallback

`load_pdf()` tries `pdfplumber` first because its `layout=True` mode
preserves horizontal spacing, which matters for resume-style PDFs with
multi-column headers, icon-font contact rows (phone/email/GitHub/LinkedIn
glyphs), and letter-spaced name headings. If pdfplumber raises or returns
no usable text for any page, `pypdf` is used as a fallback.

### Text cleaning (`clean_text`)

Every extracted document (PDF, DOCX, and TXT) passes through
`clean_text()` before chunking, which fixes the noise that most commonly
corrupted names/headings in resumes:

| Problem | Fix |
|---|---|
| `(cid:239)`-style tokens from unmapped icon-font glyphs | Stripped |
| Private-Use-Area characters (icon fonts, U+E000–U+F8FF / U+F0000–U+10FFFD) | Stripped |
| Ligatures (`ﬁ`, `ﬂ`, `ﬀ` …), smart quotes, en/em dashes | Normalized to plain ASCII equivalents |
| Words split by a line-wrap hyphen (`Ter-\nraform`) | Rejoined (`Terraform`) |
| Letter-spaced headings / repeated whitespace | Collapsed to single spaces |
| Control characters from PDF encoders | Stripped (newline/tab kept) |

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
    CHUNK_SIZE=800      # words per chunk
    CHUNK_OVERLAP=150   # overlap words between chunks
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