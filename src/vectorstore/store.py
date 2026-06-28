from typing import List, Dict

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings
from src.embedings.embedder import get_embedder


class VectorStore:
    def __init__(self):
        print(
            f"Initializing Chroma at: "
            f"{settings.chroma_persist_directory}"
        )

        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False
            ),
        )

        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self.embedder = get_embedder()

    def add_chunks(self, chunks: List[Dict]) -> int:
        if not chunks:
            print("No chunks supplied.")
            return 0

        try:
            ids = [chunk["chunk_id"] for chunk in chunks]

            texts = [
                chunk["text"]
                for chunk in chunks
            ]

            metadatas = [
                {
                    "doc_id": chunk["doc_id"],
                    "source": chunk["source"],
                }
                for chunk in chunks
            ]

            print(
                f"Generating embeddings for "
                f"{len(texts)} chunks..."
            )

            embeddings = self.embedder.embed(texts)

            print(
                f"Generated {len(embeddings)} embeddings."
            )

            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings,
            )

            current_count = self.collection.count()

            print(
                f"Collection count after insert: "
                f"{current_count}"
            )

            return len(chunks)

        except Exception as e:
            print(f"Error adding chunks: {e}")
            raise

    def query(
        self,
        query_text: str,
        top_k: int | None = None,
    ):
        top_k = top_k or settings.top_k

        query_embedding = self.embedder.embed_query(
            query_text
        )

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        output = []

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for text, metadata, distance in zip(
            docs,
            metadatas,
            distances,
        ):
            output.append(
                {
                    "text": text,
                    "doc_id": metadata.get("doc_id"),
                    "source": metadata.get("source"),
                    "distance": distance,
                }
            )

        return output

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        try:
            self.client.delete_collection(
                name=settings.chroma_collection_name
            )
            print("Collection deleted.")
        except Exception:
            print(
                "Collection did not exist. "
                "Creating fresh collection."
            )

        self.collection = (
            self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        )


_store = None


def get_vector_store() -> VectorStore:
    global _store

    if _store is None:
        _store = VectorStore()

    return _store