from src.config import settings

print("Config loaded successfully:")
print(f"Embeddings Model: {settings.embedding_model}")
print(f"LLM Model: {settings.llm_model}")
print(f"Chroma Persist Directory: {settings.chroma_persist_dir}")
print(f"Chroma Collection Name: {settings.chroma_collection_name}")
print(f"Chunk Size: {settings.chunk_size}")
print(f"Chunk Overlap: {settings.chunk_overlap}")
print(f"Top K: {settings.top_k}")