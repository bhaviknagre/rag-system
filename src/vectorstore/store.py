from typing import List, Dict, Optional
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from src.config import Settings
from src.embedings.embedder import get_embeddings
import logging
from pymongo import MongoClient
import certifi

logger = logging.getLogger(__name__)

settings = Settings()

_mongo_client: Optional[MongoClient] = None


def _get_mongo_client() -> MongoClient:
    # Built lazily so importing this module never requires MONGODB_ATLAS_URI —
    # only deployments that actually select the mongodb provider need it set.
    global _mongo_client
    if _mongo_client is None:
        if not settings.mongodb_atlas_uri:
            raise ValueError(
                "MONGODB_ATLAS_URI is not set in .env. "
                "Get it from MongoDB Atlas -> Database -> Connect -> Drivers"
            )
        _mongo_client = MongoClient(
            settings.mongodb_atlas_uri,
            tlsCAFile=certifi.where()
        )
    return _mongo_client


# Backend

def _build_chroma() -> VectorStore:
    from langchain_chroma import Chroma
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

    return Chroma(
        client=client,
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine"}
    )


def _build_pinecone() -> VectorStore:
    from langchain_pinecone import PineconeVectorStore
    from pinecone import Pinecone, ServerlessSpec
    import time

    if not settings.pinecone_api_key:
        raise ValueError("PINECONE_API_KEY is not set in .env.")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    index_name = settings.pinecone_index_name
    if index_name not in existing_indexes:
        logger.info(f"Index '{index_name}' not found. Creating it now...")
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
        logger.info(f"Index '{index_name}' is ready!")

    index = pc.Index(index_name)

    return PineconeVectorStore(
        index=index,
        embedding=get_embeddings(),
        text_key="text"
    )

def _build_mongodb() -> VectorStore:
    from langchain_mongodb import MongoDBAtlasVectorSearch

    collection = _get_mongo_client()[settings.mongodb_db_name][settings.mongodb_collection_name]

    return MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=get_embeddings(),
        index_name=settings.mongodb_vector_index_name,
        text_key="text",
        embedding_key="embedding",
        relevance_score_fn="cosine"
    )

# Backend registry
BACKEND_MAP = {
    "chroma": _build_chroma,
    "pinecone": _build_pinecone,
    "mongodb": _build_mongodb,
}

# Factory
_store_instances: Dict[str, VectorStore] = {}


def get_vector_store(provider: Optional[str] = None) -> VectorStore:
    provider = provider or settings.vector_db_provider

    if provider not in BACKEND_MAP:
        raise ValueError(
            f"Unknown vector DB provider '{provider}'. "
            f"Valid options: {list(BACKEND_MAP.keys())}"
        )

    if provider not in _store_instances:
        logger.info(f"Initializing vector store backend: {provider}")
        _store_instances[provider] = BACKEND_MAP[provider]()

    return _store_instances[provider]


# Unified operations
def add_chunks_to_store(chunks: List[Dict], provider: Optional[str] = None) -> int:
    if not chunks:
        logger.warning("No chunks provided to add_chunks_to_store")
        return 0

    store = get_vector_store(provider)

    documents = [
        Document(
            page_content=chunk["text"],
            metadata={
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "source": chunk["source"],
                "strategy": chunk.get("metadata", {}).get("strategy", "unknown"),
                "window_context": chunk.get("metadata", {}).get("window_context", "")
            }
        )
        for chunk in chunks
    ]

    ids = [chunk["chunk_id"] for chunk in chunks]

    store.add_documents(documents=documents, ids=ids)
    logger.info(f"Added {len(documents)} chunks to {provider or settings.vector_db_provider}")
    return len(documents)


def query_store(query: str, top_k: Optional[int] = None, provider: Optional[str] = None) -> List[Dict]:
    store = get_vector_store(provider)
    top_k = top_k or settings.top_k

    results = store.similarity_search_with_relevance_scores(
        query=query,
        k=top_k
    )

    output = []
    for doc, score in results:
        output.append({
            "text": doc.page_content,
            "doc_id": doc.metadata.get("doc_id", "unknown"),
            "source": doc.metadata.get("source", ""),
            "score": round(score, 4),
            "window_context": doc.metadata.get("window_context", ""),
            "strategy": doc.metadata.get("strategy", "")
        })

    return output


def reset_store(provider: Optional[str] = None):
    provider = provider or settings.vector_db_provider
    if provider in _store_instances:
        del _store_instances[provider]

    if provider == "chroma":
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        try:
            client.delete_collection(settings.chroma_collection_name)
            logger.info(f"Chroma collection '{settings.chroma_collection_name}' deleted")
        except Exception as e:
            logger.warning(f"Could not delete Chroma collection (may not exist yet): {e}")

    elif provider == "pinecone":
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.pinecone_api_key)

        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if settings.pinecone_index_name in existing_indexes:
            index = pc.Index(settings.pinecone_index_name)
            try:
                index.delete(delete_all=True)
                logger.info(f"Pinecone index '{settings.pinecone_index_name}' cleared")
            except Exception as e:
                if "Namespace not found" in str(e):
                    logger.info(f"Pinecone index '{settings.pinecone_index_name}' is already completely empty.")
                else:
                    logger.warning(f"Could not clear Pinecone index: {e}")
        else:
            logger.warning(f"Pinecone index '{settings.pinecone_index_name}' does not exist yet. Skipping reset.")

    elif provider == "mongodb":
        # Use the shared client with SSL configuration attached
        _get_mongo_client()[settings.mongodb_db_name][settings.mongodb_collection_name].drop()
        logger.info(f"MongoDB collection '{settings.mongodb_collection_name}' dropped")


def count_chunks(provider: Optional[str] = None) -> int:
    provider = provider or settings.vector_db_provider

    try:
        if provider == "chroma":
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            col = client.get_or_create_collection(settings.chroma_collection_name)
            return col.count()

        elif provider == "pinecone":
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.pinecone_api_key)
            index = pc.Index(settings.pinecone_index_name)
            stats = index.describe_index_stats()
            return stats.total_vector_count

        elif provider == "mongodb":
            # Use the shared client with SSL configuration attached
            return _get_mongo_client()[settings.mongodb_db_name][settings.mongodb_collection_name].count_documents({})

    except Exception as e:
        logger.warning(f"Could not count chunks for {provider}: {e}")
        return -1

    return 0


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    provider = "pinecone"

    from src.ingestion.loader import load_documents_from_directory
    from src.ingestion.chunker import chunk_documents

    print(f"Testing vector store backend: {provider}\n")

    raw_docs = load_documents_from_directory()
    chunks = chunk_documents(raw_docs, strategy="recursive")
    print(f"Chunks ready: {len(chunks)}")

    print("Resetting store...")
    reset_store(provider)

    print("Adding chunks...")
    added = add_chunks_to_store(chunks, provider=provider)
    print(f"Added: {added} chunks")
    print(f"Total in store: {count_chunks(provider)}")

    print("\nRunning test query...")
    results = query_store("What is this document about?", top_k=2, provider=provider)
    for r in results:
        print(f"  [{r['doc_id']}] score={r['score']} | {r['text'][:100]}...")