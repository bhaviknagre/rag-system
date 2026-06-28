from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    openai_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "llama3.2:1b"
    ollama_base_url: str = "http://localhost:11434"

    chroma_persist_directory: str = "./data/vectorstore"
    chroma_collection_name: str = "rag_documents"

    documents_directory: str = "./data/raw"

    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra="ignore"
    
settings = Settings()

Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)