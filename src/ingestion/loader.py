from pathlib import Path
from typing import List, Optional, Dict
from pypdf import PdfReader
from docx import Document as DocxDocument

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt"]

def load_text(file_path: str) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")

def load_pdf(file_path: str) -> str:
    reader = PdfReader(str(file_path))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)

def load_docx(file_path: str) -> str:
    doc = DocxDocument(str(file_path))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

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
