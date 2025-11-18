from pinecone import Pinecone
from ..core.config import settings

pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(settings.PINECONE_INDEX_NAME)

def query_pinecone(query: str, top_k: int = 5):
    results = index.query(vector=query,  # vector will be added by embedding
                          top_k=top_k,
                          include_metadata=True)
    return results