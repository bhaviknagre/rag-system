from typing import Dict

from src.ingestion.loader import load_documents_from_directory
from src.ingestion.chunker import chunk_documents
from src.vectorstore.store import get_vector_store
from src.retrieval.retriever import get_retriever
from src.generation.generator import get_generator
from src.config import settings


def raw_ingest(raw_dir: str = "data/raw", reset: bool = False):
    store = get_vector_store()

    if reset:
        print("[INGEST] Resetting vector store")
        store.reset()

    print(f"[INGEST] Loading from {raw_dir}")
    documents = load_documents_from_directory(raw_dir)

    print(f"[INGEST] Documents loaded: {len(documents)}")
    if not documents:
        return {"status": "no_documents"}

    chunks = chunk_documents(documents)

    print(f"[INGEST] Chunks created: {len(chunks)}")

    if len(chunks) == 0:
        return {"status": "no_chunks"}

    print("[INGEST] First chunk preview:", chunks[0])

    added = store.add_chunks(chunks)

    print(f"[INGEST] Added to vector store: {added}")
    print(f"[INGEST] Total in DB: {store.count()}")

    return {
        "status": "success",
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "chunks_added": added,
        "total_chunks_in_store": store.count()
    }


def ask(question: str, top_k: int | None = None) -> Dict:
    retriever = get_retriever()
    generator = get_generator()

    top_k = top_k or settings.top_k

    retrieved_chunks = retriever.retrieve(question, top_k=top_k)
    context = retriever.retrieve_context(question, top_k=top_k)

    answer = generator.generate(question, context)

    sources = [
        {
            "doc_id": chunk["doc_id"],
            "source": chunk["source"],
            "distance": round(chunk["distance"], 4),
        }
        for chunk in retrieved_chunks
    ]

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
    }


if __name__ == "__main__":
    print("Ingesting documents...\n")

    summary = raw_ingest(
        raw_dir=settings.documents_directory,
        reset=True,
    )

    print("\nIngestion Summary")
    print(summary)

    print("\nTesting question answering...\n")

    response = ask("What is the main topic of the documents?")

    print(f"Question: {response['question']}")
    print(f"Answer: {response['answer']}")

    print("\nSources:")
    for source in response["sources"]:
        print(
            f"- {source['source']} "
            f"(distance={source['distance']})"
        )