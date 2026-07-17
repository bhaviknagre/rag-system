import re
import unicodedata
from pathlib import Path
from typing import List, Dict

from pypdf import PdfReader
from docx import Document as DocxDocument

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt"]

_LIGATURE_MAP = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st",
    "•": "- ", "●": "- ", "▪": "- ",  
    "–": "-", "—": "-",  
    "‘": "'", "’": "'", "“": '"', "”": '"',
    " ": " ",  
}


def clean_text(text: str) -> str:
    """Normalize PDF/DOCX extraction noise so downstream chunking/embedding
    sees clean, well-formed text instead of garbled ligatures, hyphen-wrapped
    words, and irregular whitespace (common causes of dropped/corrupted names
    and headings in resumes)."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    for bad, good in _LIGATURE_MAP.items():
        text = text.replace(bad, good)

    text = re.sub(r"\(cid:\d+\)", " ", text)

    text = "".join(
        ch for ch in text
        if not (0xE000 <= ord(ch) <= 0xF8FF or 0xF0000 <= ord(ch) <= 0x10FFFD)
    )

    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or unicodedata.category(ch)[0] != "C")

    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)

    return text.strip()


def load_text(file_path: Path) -> str:
    return clean_text(Path(file_path).read_text(encoding="utf-8", errors="ignore"))


def _extract_pdf_with_pdfplumber(file_path: str) -> List[str]:
    import pdfplumber

    text_parts = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3)
            if text:
                text_parts.append(text)
    return text_parts


def _extract_pdf_with_pypdf(file_path: str) -> List[str]:
    reader = PdfReader(str(file_path))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return text_parts


def load_pdf(file_path: str) -> str:
    """Extract text from a PDF, preferring pdfplumber for its layout-aware
    parsing (more reliable on resumes with columns/tables/headers) and
    falling back to pypdf if pdfplumber fails or returns nothing usable."""
    text_parts: List[str] = []

    try:
        text_parts = _extract_pdf_with_pdfplumber(file_path)
    except Exception:
        text_parts = []

    if not any(part.strip() for part in text_parts):
        text_parts = _extract_pdf_with_pypdf(file_path)

    raw_text = "\n".join(text_parts)
    return clean_text(raw_text)


def load_docx(file_path: str) -> str:
    doc = DocxDocument(str(file_path))
    raw_text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    return clean_text(raw_text)


def load_document(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(file_path)
    elif suffix == ".docx":
        return load_docx(file_path)
    elif suffix == ".txt":
        return load_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Supported types are: {SUPPORTED_EXTENSIONS}")


def load_documents_from_directory(raw_dir: str = "data/raw") -> List[Dict]:
    raw_path = Path(raw_dir)
    document = []

    for file_path in sorted(raw_path.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                text = load_document(file_path)
                if text.strip():
                    document.append({
                        "doc_id": file_path.name,
                        "text": text,
                        "source": str(file_path)
                    })
                else:
                    print(f"Warning: {file_path.name} is empty and will be skipped.")
            except Exception as e:
                print(f"Error loading {file_path.name}: {e}")
    return document


if __name__ == "__main__":
    documents = load_documents_from_directory()
    print(f"Loaded {len(documents)} documents.")
    for doc in documents:
        print(f"Document ID: {doc['doc_id']}, Source: {doc['source']}, Text Length: {len(doc['text'])} characters")
