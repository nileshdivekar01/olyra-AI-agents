import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from Subhash_Postgres_SQL_Lead_Storage.Backend.new_content import process_and_save_pdfs, process_and_save_urls, delete_and_recreate_index, clear_pinecone_index
from Subhash_Postgres_SQL_Lead_Storage.Backend.cx_support_agent import answer_question, DOMAIN_INSTRUCTIONS
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - QueryID: %(query_id)s - ConversationID: %(conversation_id)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("customer_support.log", mode="a")]
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer-support", tags=["Customer Support Agent"])

class ConfigRequest(BaseModel):
    domain_instructions: str

class QuestionRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

@router.post("/set_config")
async def set_config(req: ConfigRequest):
    query_id = str(uuid.uuid4())
    logger.info(f"Received config request: {req.domain_instructions[:100]}...", extra={"query_id": query_id, "conversation_id": "N/A"})
    try:
        if not req.domain_instructions.strip():
            logger.warning("Empty domain instructions provided", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({"error": "Domain instructions cannot be empty. Please provide valid instructions."}, status_code=400)
        global DOMAIN_INSTRUCTIONS
        DOMAIN_INSTRUCTIONS = req.domain_instructions
        logger.info(f"Set domain instructions: {DOMAIN_INSTRUCTIONS[:100]}...", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"message": "Configuration applied successfully! The agent is now adapted to your settings."})
    except Exception as e:
        logger.error(f"Error setting config: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to apply configuration. Please try again or contact support."}, status_code=500)

@router.get("/", response_class=HTMLResponse)
async def index():
    query_id = str(uuid.uuid4())
    logger.info("Serving index page", extra={"query_id": query_id, "conversation_id": "N/A"})
    try:
        return """
        <h2>PDF and URL Question Answering API</h2>
        <p>Use <b>/customer-support/upload_pdf</b> to upload PDFs and <b>/customer-support/upload_url</b> to upload URLs (comma-separated).</p>
        <p>Use <b>/customer-support/ask</b> to query the index.</p>
        <p>For either upload endpoint, use clear_index=true with no content to delete and recreate the index.</p>
        <p>Use <b>/customer-support/clear_index</b> to clear the vector index.</p>
        """
    except Exception as e:
        logger.error(f"Error serving index page: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return HTMLResponse(content="Error: Unable to load the index page. Please try again later.", status_code=500)

@router.post("/upload_pdf")
async def upload_pdf(pdf_files: List[UploadFile] = File([]), clear_index: bool = Form(False)):
    query_id = str(uuid.uuid4())
    logger.info(f"Received PDF upload request, clear_index={clear_index}", extra={"query_id": query_id, "conversation_id": "N/A"})
    file_paths = []
    try:
        if clear_index and len(pdf_files) == 0:
            logger.debug("Attempting to delete and recreate Pinecone index", extra={"query_id": query_id, "conversation_id": "N/A"})
            try:
                delete_and_recreate_index()
                logger.info("Index deleted and recreated successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"message": "Index deleted and recreated successfully!"})
            except Exception as e:
                logger.error(f"Failed to delete and recreate index: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"error": "Failed to reset the index. Please try again or contact support."}, status_code=500)
        if len(pdf_files) == 0:
            logger.warning("No PDFs provided", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({"error": "No PDFs provided. Please upload at least one PDF file."}, status_code=400)
        file_names = [pdf.filename for pdf in pdf_files]
        logger.info(f"Processing PDFs: {file_names}", extra={"query_id": query_id, "conversation_id": "N/A"})
        for pdf in pdf_files:
            logger.debug(f"Saving PDF file: {pdf.filename}", extra={"query_id": query_id, "conversation_id": "N/A"})
            temp_path = f"temp_{pdf.filename}"
            try:
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(pdf.file, buffer)
                file_paths.append(temp_path)
            except Exception as e:
                logger.error(f"Failed to save PDF {pdf.filename}: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                raise
        logger.debug("Calling process_and_save_pdfs", extra={"query_id": query_id, "conversation_id": "N/A"})
        try:
            process_and_save_pdfs(file_paths, clear_index=clear_index)
            logger.info("PDFs processed successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
        except Exception as e:
            logger.error(f"Failed to process PDFs: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
            raise
        for path in file_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up temp file: {path}", extra={"query_id": query_id, "conversation_id": "N/A"})
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {path}: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"message": "PDFs processed and vectors added to the index successfully!"})
    except Exception as e:
        for path in file_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up temp file on error: {path}", extra={"query_id": query_id, "conversation_id": "N/A"})
                except Exception as e_cleanup:
                    logger.warning(f"Failed to clean up temp file {path} on error: {str(e_cleanup)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        logger.error(f"Error processing PDFs: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to process PDFs. Please check your files and try again."}, status_code=500)

@router.post("/upload_url")
async def upload_url(urls: str = Form(""), clear_index: bool = Form(False)):
    query_id = str(uuid.uuid4())
    logger.info(f"Received URL upload request, urls={urls}, clear_index={clear_index}", extra={"query_id": query_id, "conversation_id": "N/A"})
    try:
        urls_list = [u.strip() for u in urls.split(',') if u.strip()]
        if clear_index and not urls_list:
            logger.debug("Attempting to delete and recreate Pinecone index", extra={"query_id": query_id, "conversation_id": "N/A"})
            try:
                delete_and_recreate_index()
                logger.info("Index deleted and recreated successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"message": "Index deleted and recreated successfully!"})
            except Exception as e:
                logger.error(f"Failed to delete and recreate index: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"error": "Failed to reset the index. Please try again or contact support."}, status_code=500)
        if not urls_list:
            logger.warning("No URLs provided", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({"error": "No URLs provided. Please provide at least one valid URL."}, status_code=400)
        logger.debug(f"Processing URLs: {urls_list}", extra={"query_id": query_id, "conversation_id": "N/A"})
        try:
            process_and_save_urls(urls_list, clear_index=clear_index)
            logger.info("URLs processed successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
        except Exception as e:
            logger.error(f"Failed to process URLs: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
            if str(e) == "Website owner does not allow content access":
                return JSONResponse({"error": "Website owner does not allow content access. Please check the URLs and try again."}, status_code=403)
            raise
        return JSONResponse({"message": "URLs processed and vectors added to the index successfully!"})
    except Exception as e:
        logger.error(f"Error processing URLs: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to process URLs. Please check your URLs and try again."}, status_code=500)

@router.post("/ask")
async def ask_question(request: Request, req: QuestionRequest):
    query_id = str(uuid.uuid4())
    conversation_id = req.conversation_id or str(uuid.uuid4())
    logger.info(f"Received raw request body: {await request.json()}", extra={"query_id": query_id, "conversation_id": conversation_id})
    logger.info(f"Received question: {req.question}", extra={"query_id": query_id, "conversation_id": conversation_id})
    try:
        if not req.question.strip():
            logger.warning("Empty question provided", extra={"query_id": query_id, "conversation_id": conversation_id})
            return JSONResponse({"error": "No question provided. Please ask a question to proceed.", "conversation_id": conversation_id}, status_code=400)
        logger.debug("Calling answer_question", extra={"query_id": query_id, "conversation_id": conversation_id})
        try:
            response = answer_question(req.question, req.conversation_id)
            logger.info(f"Response: {response['answer'][:500]}...", extra={"query_id": query_id, "conversation_id": conversation_id})
            return JSONResponse(response)
        except Exception as e:
            logger.error(f"Failed to process question: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id})
            return JSONResponse({"error": "Unable to process your question. Please try again or contact support.", "conversation_id": conversation_id}, status_code=500)
    except ValidationError as e:
        logger.error(f"Validation error in ask_question: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id})
        return JSONResponse({"error": f"Invalid request payload: {str(e)}", "conversation_id": conversation_id}, status_code=422)
    except Exception as e:
        logger.critical(f"Critical error in ask_question: {str(e)}", extra={"query_id": query_id, "conversation_id": conversation_id})
        return JSONResponse({"error": "An unexpected error occurred. Please try again later or contact support.", "conversation_id": conversation_id}, status_code=500)

@router.post("/clear_index")
async def clear_index():
    query_id = str(uuid.uuid4())
    logger.info("Received clear index request", extra={"query_id": query_id, "conversation_id": "N/A"})
    try:
        logger.debug("Attempting to clear Pinecone index", extra={"query_id": query_id, "conversation_id": "N/A"})
        clear_pinecone_index()
        logger.info("Index cleared successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"message": "Vector index cleared successfully!"})
    except Exception as e:
        logger.error(f"Error clearing index: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to clear the index. Please try again or contact support."}, status_code=500)