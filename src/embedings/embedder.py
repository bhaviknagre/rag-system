from typing import List
from sentence_transformers import SentenceTransformer
from src.config import settings


class Embedder:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._model = SentenceTransformer(settings.embedding_model)
        return cls._instance

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        return self.embed([query])[0]


_embedder = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


if __name__ == "__main__":
    embedder = get_embedder()

    sample = [
        "This is a sample sentence for embedding.",
        "Another example sentence."
    ]

    vectors = embedder.embed(sample)

    print(f"Generated {len(vectors)} embeddings for {len(sample)} sentences.")
    print(f"Embedding dimensions: {len(vectors[0])}")