import os
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
# from pinecone import Pinecone, ServerlessSpec
from pinecone import Pinecone , ServerlessSpec
from dotenv import load_dotenv
from ..core.config import settings

load_dotenv()

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

# Init Pinecone
pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index_name = settings.PINECONE_INDEX_NAME

# Create index if not exists
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=786,   # Gemini embeddings dimension
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(index_name)

def gemini_embed(text: str):
    """Generate embeddings from Gemini"""
    resp = genai.embed_content(model="models/embedding-001", content=text)
    return resp["embedding"]

def store_pdf_to_pinecone(file_path: str):
    """Load PDF → Embed chunks → Store in Pinecone"""
    loader = PyPDFLoader(file_path)
    docs = loader.load_and_split()
    project_name = "AI Production Scheduler"
    vectors = []
    for i, doc in enumerate(docs):
        emb = gemini_embed(doc.page_content)
        vectors.append({
            "id": f"{project_name}__doc_{i}",
            "values": emb,
            "metadata": {"Text": doc.page_content,"Project Name":project_name}
        })

    index.upsert(vectors=vectors)
    return {"status": "success", "docs_indexed": len(vectors)}
