from typing import List, Dict
from src.config import settings

def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None):
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    text = text.replace("\n", " ").strip()
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])

        chunks.append(chunk)

        start += max(1, chunk_size - chunk_overlap)

    return chunks

def chunk_documents(documents: List[Dict]) -> List[Dict]:
    all_chunks = []
    for doc in documents:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "chunk_id": f"{doc['doc_id']}_chunk_{i}",
                "doc_id": doc["doc_id"],
                "text": chunk,
                "source": doc["source"]
            })
    return all_chunks

if __name__ == "__main__":
    from src.ingestion.loader import load_documents_from_directory
    documents = load_documents_from_directory()
    chunked_documents = chunk_documents(documents)
    print(f"Created {len(chunked_documents)} chunks from {len(documents)} documents")
    if chunked_documents:
        print(f"First chunk: {chunked_documents[0]}")
        