from typing import List, Dict, Optional
from src.vectorstore.store import query_store
from src.config import settings

class Retriever:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider

    def retrieve(self, query: str, top_k: int | None = None) -> List[Dict]:
        top_k = top_k or settings.top_k
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        results = query_store(query, top_k=top_k, provider=self.provider)
        return results
    def retrieve_context(self, query: str, top_k: int | None = None) -> str:
        result = self.retrieve(query, top_k=top_k)
        if not result:
            return ""
        context_parts = []
        for i, r in enumerate(result, start=1):
            context_parts.append(f"Chunk {i} (Doc ID: {r['doc_id']}, Source: {r['source']}):\n{r['text']}\n")
        return "\n".join(context_parts)

_retriever = None

def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever

if __name__ == "__main__":
    retriever = get_retriever()
    query = "What is the main topic of the documents?"
    print(f"Query: {query}\n")
    results = retriever.retrieve(query, top_k=3)
    print(f"Retrieved {len(results)} chunks:\n")
    for r in results:
        print(f"Doc ID: {r['doc_id']}, Source: {r['source']}, Score: {r['score']}\nText: {r['text']}\n")

    print(f"\nRetrieving context for the query:\n")
    context = retriever.retrieve_context(query, top_k=3)
    print(context)
