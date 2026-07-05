from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    llm_model: str = "llama3.2:1b"
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_db_provider: Literal["chroma", "pinecone", "mongodb"] = "chroma"
    chroma_persist_dir: str = "./data/vectorstore"
    chroma_collection_name: str = "rag_documents"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "rag-system-index"
    mongodb_atlas_uri: str = "mongodb+srv://<bhavik>:<bhaviknagre143>@cluster0.lmijouj.mongodb.net/"
    mongodb_db_name: str = "rag_system"
    mongodb_collection_name: str = "document_chunks"
    mongodb_vector_index_name: str = "vector_index"
    chunking_strategy: Literal["recursive", "semantic", "sentence_window"] = "recursive"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)