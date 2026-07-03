from langchain_huggingface import HuggingFaceEmbeddings
from src.config import settings

_embeddings_instance = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings_instance


if __name__ == "__main__":
    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(["test sentence one", "test sentence two"])
    print(f"Generated {len(vectors)} embeddings")
    print(f"Embedding dimension: {len(vectors[0])}")

    query_vector = embeddings.embed_query("a test query")
    print(f"Query embedding dimension: {len(query_vector)}")