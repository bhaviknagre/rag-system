from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter,
)
from langchain_experimental.text_splitter import SemanticChunker
from src.config import settings
from src.embedings.embedder import get_embeddings
import re

#Helper function
def _dicts_to_documents(raw_docs: List[Dict]) -> List[Document]:
    return [
        Document(
            page_content=doc["text"],
            metadata={
                "doc_id": doc["doc_id"],
                "source": doc["source"]
            }
        )
        for doc in raw_docs
    ]


def _documents_to_chunks(docs: List[Document], strategy: str) -> List[Dict]:
    chunks = []
    counter: Dict[str, int] = {}

    for doc in docs:
        doc_id = doc.metadata.get("doc_id", "unknown")
        counter[doc_id] = counter.get(doc_id, 0)
        chunk_id = f"{doc_id}_{strategy}_chunk_{counter[doc_id]}"
        counter[doc_id] += 1

        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "source": doc.metadata.get("source", ""),
            "text": doc.page_content,
            "metadata": {
                **doc.metadata,
                "strategy": strategy,
                "chunk_index": counter[doc_id] - 1,
                "window_context": doc.metadata.get("window_context", "")
            }
        })

    return chunks

# Strategy 1: Recursive Character Splitting
def recursive_chunk(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len
    )
    return splitter.split_documents(documents)

# Strategy 2: Semantic Chunking
def semantic_chunk(documents: List[Document]) -> List[Document]:
    embeddings = get_embeddings()
    splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90
    )
    return splitter.split_documents(documents)


# Strategy 3: Sentence Window Chunking
def _split_into_sentences(text: str) -> List[str]:
    """Simple regex sentence splitter (avoids heavy NLP dependency)."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def sentence_window_chunk(documents: List[Document],window_size: int = 2) -> List[Document]:
    chunked_docs = []

    for doc in documents:
        sentences = _split_into_sentences(doc.page_content)
        total = len(sentences)

        for i, sentence in enumerate(sentences):
            # Build surrounding window
            window_start = max(0, i - window_size)
            window_end = min(total, i + window_size + 1)
            window_sentences = sentences[window_start:window_end]
            window_context = " ".join(
                s for s in window_sentences if s != sentence
            )

            chunked_docs.append(
                Document(
                    page_content=sentence,
                    metadata={
                        **doc.metadata,
                        "window_context": window_context,
                        "sentence_index": i,
                        "total_sentences": total
                    }
                )
            )

    return chunked_docs

# Public API
STRATEGY_MAP = {
    "recursive": recursive_chunk,
    "semantic": semantic_chunk,
    "sentence_window": sentence_window_chunk,
}


def chunk_documents(raw_docs: List[Dict],strategy: str = None) -> List[Dict]:
    strategy = strategy or settings.chunking_strategy

    if strategy not in STRATEGY_MAP:
        raise ValueError(
            f"Unknown chunking strategy '{strategy}'. "
            f"Valid options: {list(STRATEGY_MAP.keys())}"
        )

    lc_documents = _dicts_to_documents(raw_docs)
    chunker_fn = STRATEGY_MAP[strategy]
    chunked_lc_docs = chunker_fn(lc_documents)
    chunks = _documents_to_chunks(chunked_lc_docs, strategy)

    return chunks


if __name__ == "__main__":
    from src.ingestion.loader import load_documents_from_directory

    raw_docs = load_documents_from_directory()
    print(f"Loaded {len(raw_docs)} documents\n")

    for strategy in ["recursive", "semantic", "sentence_window"]:
        print(f"--- Strategy: {strategy} ---")
        try:
            chunks = chunk_documents(raw_docs, strategy=strategy)
            print(f"  Chunks produced : {len(chunks)}")
            print(f"  Sample chunk    : {chunks[0]['text'][:120]}...")
            if chunks[0]["metadata"].get("window_context"):
                print(f"  Window context  : {chunks[0]['metadata']['window_context'][:120]}...")
        except Exception as e:
            print(f" Failed: {e}")
        print()