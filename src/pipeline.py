import logging
from typing import Dict, Optional

from src.config import Settings
from src.ingestion.loader import load_documents_from_directory
from src.ingestion.chunker import chunk_documents
from src.vectorstore.store import (
    add_chunks_to_store,
    query_store,
    reset_store,
    count_chunks
)
from src.generation.generator import get_generator

logger = logging.getLogger(__name__)
settings = Settings()


def _build_context(retrieved_chunks: list) -> str:
    if not retrieved_chunks:
        return ""

    parts = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        text = chunk["text"]
        window = chunk.get("window_context", "")
        if window:
            text = f"{window}\n[Focus]: {text}"

        parts.append(f"[Source {i}: {chunk['doc_id']}]\n{text}")

    return "\n\n".join(parts)


def ingest(
    raw_dir: str = "data/raw",
    provider: Optional[str] = None,
    strategy: Optional[str] = None,
    reset: bool = False,
) -> Dict:
    provider = provider or settings.vector_db_provider
    strategy = strategy or settings.chunking_strategy

    logger.info(f"Starting ingestion | provider={provider} | strategy={strategy} | reset={reset}")

    if reset:
        logger.info(f"Resetting store: {provider}")
        reset_store(provider)

    raw_docs = load_documents_from_directory(raw_dir)
    if not raw_docs:
        return {
            "status": "no_documents_found",
            "provider": provider,
            "strategy": strategy,
            "documents_loaded": 0,
            "chunks_created": 0,
            "chunks_added": 0,
            "total_chunks_in_store": count_chunks(provider)
        }

    chunks = chunk_documents(raw_docs, strategy=strategy)
    added = add_chunks_to_store(chunks, provider=provider)

    summary = {
        "status": "success",
        "provider": provider,
        "strategy": strategy,
        "documents_loaded": len(raw_docs),
        "chunks_created": len(chunks),
        "chunks_added": added,
        "total_chunks_in_store": count_chunks(provider)
    }

    logger.info(f"Ingestion complete: {summary}")
    return summary


def ask(
    question: str,
    provider: Optional[str] = None,
    top_k: Optional[int] = None,
) -> Dict:
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    provider = provider or settings.vector_db_provider
    top_k = top_k or settings.top_k

    logger.info(f"Query received | provider={provider} | question={question[:60]}")

    retrieved = query_store(
        query=question,
        top_k=top_k,
        provider=provider
    )
    context = _build_context(retrieved)
    generator = get_generator()
    answer = generator.generate(question=question, context=context)

    sources = [
        {
            "doc_id": r["doc_id"],
            "source": r["source"],
            "score": r["score"],
            "strategy": r.get("strategy", "")
        }
        for r in retrieved
    ]

    return {
        "question": question,
        "answer": answer,
        "provider": provider,
        "sources": sources
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    provider = "chroma"
    strategy = "recursive"

    print(f"=== Ingesting | provider={provider} | strategy={strategy} ===")
    summary = ingest(provider=provider, strategy=strategy, reset=True)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n=== Asking | provider={provider} ===")
    result = ask("What is this document about?", provider=provider)
    print(f"\nQuestion : {result['question']}")
    print(f"Answer   : {result['answer']}")
    print(f"Provider : {result['provider']}")
    print("\nSources:")
    for s in result["sources"]:
        print(f"  [{s['doc_id']}] score={s['score']} | strategy={s['strategy']}")