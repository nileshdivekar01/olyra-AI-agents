# new_content.py (updated)
import os
from typing import List, Dict
from PyPDF2 import PdfReader
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm
from dotenv import load_dotenv
from bs4 import BeautifulSoup  # web url text extracting
import requests  # Added for fetching web content
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY_SUPPORT_AGENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_SUPPORT_AGENT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME_SUPPORT_AGENT", "talita-alves-vector-index")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)



def initialize_pinecone_index(index_name: str, dimension: int = 1536, metric: str = "cosine"):
    """Initialize Pinecone index with error handling"""
    try:
        if index_name not in [idx["name"] for idx in pc.list_indexes()]:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            logger.info(f"Created Pinecone index: {index_name}")
        else:
            logger.info(f"Pinecone index already exists: {index_name}")
        return pc.Index(index_name)
    except Exception as e:
        logger.critical(f"Pinecone index initialization error: {e}")
        return None




def clear_pinecone_index(index_name: str = PINECONE_INDEX):
    """Delete all vectors from the specified Pinecone index"""
    try:
        index = pc.Index(index_name)
        # Delete all vectors in the index
        index.delete(delete_all=True)
        logger.info(f"Successfully cleared all vectors from Pinecone index: {index_name}")
    except Exception as e:
        logger.error(f"Error clearing Pinecone index {index_name}: {e}")
        raise



def delete_and_recreate_index(index_name: str = PINECONE_INDEX):
    """Delete the Pinecone index if it exists and recreate it"""
    try:
        if index_name in [idx["name"] for idx in pc.list_indexes()]:
            pc.delete_index(index_name)
            logger.info(f"Deleted Pinecone index: {index_name}")
        initialize_pinecone_index(index_name)
        logger.info(f"Recreated Pinecone index: {index_name}")
    except Exception as e:
        logger.error(f"Error deleting and recreating index {index_name}: {e}")
        raise




def get_pdf_text(pdf_path: str) -> str:
    """Extract text from a single PDF"""
    text = ""
    try:
        pdf_reader = PdfReader(pdf_path)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        logger.info(f"Extracted text from PDF: {pdf_path}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""



def get_web_text(url: str) -> str:
    """Fetch and clean text from a web URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.extract()
        page_text = soup.get_text(separator='\n', strip=True)
        logger.info(f"Extracted and cleaned text from URL: {url}")
        logger.info(f"Content length: {len(page_text)} characters")
        logger.info(f"Full content:\n{page_text}")
        return page_text
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"Access forbidden for URL {url}: Website owner does not allow content access")
            raise Exception("Website owner does not allow content access")
        logger.error(f"HTTP error fetching URL {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Error fetching or cleaning URL {url}: {e}")
        return ""



def get_text_chunks(text: str, max_chars: int = 1000) -> List[str]:
    """Split text into manageable chunks"""
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chars,
            chunk_overlap=100,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error splitting text: {e}")
        return []




def save_documents(documents: List[Dict[str, str]], index_name: str = PINECONE_INDEX, batch_size: int = 100, clear_index: bool = False):
    """Save documents to Pinecone vector store with batch processing and appending"""
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)
        index = initialize_pinecone_index(index_name)
        if index is None:
            logger.warning("Skipping Pinecone upload due to index error")
            return

        # Clear the index if requested
        if clear_index:
            clear_pinecone_index(index_name)

        # Get current vector count
        stats = index.describe_index_stats()
        current_count = stats.get('total_vector_count', 0)

        # Prepare chunks with sources
        chunk_data = []
        for doc in documents:
            chunks = get_text_chunks(doc['text'])
            for chunk in chunks:
                chunk_data.append((chunk, doc['source'], doc['type']))

        vectors = []
        for idx, (chunk, source, source_type) in enumerate(tqdm(chunk_data, desc="Embedding chunks")):
            embedding = embeddings.embed_query(chunk)
            doc_id = f"{source_type}_chunk_{current_count + idx}"
            metadata = {
                "chunk_index": current_count + idx + 1,
                "chunk_text": chunk,
                "source": source,
                "source_type": source_type,
                "chunk_for": "talita_alves_customer_support"
            }
            vectors.append({"id": doc_id, "values": embedding, "metadata": metadata})

        for i in tqdm(range(0, len(vectors), batch_size), desc="Upserting to Pinecone"):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)

        logger.info(f"Upserted {len(vectors)} new vectors to Pinecone index: {index_name}. Total now: {current_count + len(vectors)}")
    except Exception as e:
        logger.error(f"Error saving vectors to Pinecone: {e}")
        raise




def process_and_save_pdfs(pdf_paths: List[str], clear_index: bool = False):
    """Process and save PDFs to Pinecone"""
    documents = []
    for path in pdf_paths:
        text = get_pdf_text(path)
        if text:
            documents.append({"text": text, "source": os.path.basename(path), "type": "pdf"})
    if documents:
        save_documents(documents, clear_index=clear_index)




def process_and_save_urls(urls: List[str], clear_index: bool = False):
    """Process and save URLs to Pinecone"""
    documents = []
    for url in urls:
        text = get_web_text(url)
        if text:
            documents.append({"text": text, "source": url, "type": "url"})
    if documents:
        save_documents(documents, clear_index=clear_index)



def get_retriever(index_name: str = PINECONE_INDEX):
    """Get the vector store retriever"""
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)
        index = pc.Index(index_name)
        vector_store = PineconeVectorStore(index, embeddings, text_key="chunk_text")
        return vector_store.as_retriever(search_kwargs={"k": 3})
    except Exception as e:
        logger.error(f"Error creating retriever: {e}")
        return None