from pydantic import BaseModel, Field
from typing import List, Optional

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The question to ask the RAG system")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")

class SourceItem(BaseModel):
    doc_id: str
    source: str
    distance: float

class AskResponse(BaseModel): 
    question: str
    answer: str
    sources: List[SourceItem]

class IngestRequest(BaseModel):
    reset: bool = Field(False, description="If true, wipes the vector store befoew ingestiong")

class IngestResponse(BaseModel):
    status: str
    documents_loaded: int
    chunks_created: int = 0
    chunks_added: int = 0
    total_chunks_in_store: int = 0

class HealthResponse(BaseModel):
    status: str
    vector_store_chunks: int
    embedding_model: str
    llm_model: str