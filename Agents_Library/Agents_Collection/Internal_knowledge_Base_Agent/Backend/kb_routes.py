import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from Internal_knowledge_Base_Agent.Backend.kb_new_content import process_and_save_files, process_and_save_urls, delete_and_recreate_index, clear_pinecone_index
from Internal_knowledge_Base_Agent.Backend.kb_assistant import answer_question, DOMAIN_INSTRUCTIONS
import logging
import pandas as pd
from .data_analysis_agent import _save_df, answer_data_query
from .classifier import classify_query
from .kb_assistant import answer_question as answer_rag


# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - QueryID: %(query_id)s - ConversationID: %(conversation_id)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("kb_assistant.log", mode="a")]
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/new-knowledge-base", tags=["Knowledge Base Assistant"])

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
        return JSONResponse({"message": "Configuration applied successfully! The assistant is now adapted to your settings."})
    except Exception as e:
        logger.error(f"Error setting config: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to apply configuration. Please try again."}, status_code=500)



@router.get("/", response_class=HTMLResponse)
async def index():
    query_id = str(uuid.uuid4())
    logger.info("Serving index page", extra={"query_id": query_id, "conversation_id": "N/A"})
    try:
        return """
        <h2>Knowledge Base Assistant API</h2>
        <p>Use <b>/knowledge-base/upload_files</b> to upload PDFs or TXT files and <b>/knowledge-base/upload_url</b> to upload URLs (comma-separated).</p>
        <p>Use <b>/knowledge-base/ask</b> to query the knowledge base.</p>
        <p>For either upload endpoint, use clear_index=true with no content to delete and recreate the index.</p>
        <p>Use <b>/knowledge-base/clear_index</b> to clear the vector index.</p>
        """
    except Exception as e:
        logger.error(f"Error serving index page: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return HTMLResponse(content="Error: Unable to load the index page. Please try again later.", status_code=500)


''' 
@router.post("/upload_files")
async def upload_files(files: List[UploadFile] = File([]), clear_index: bool = Form(False)):
    query_id = str(uuid.uuid4())
    logger.info(f"Received file upload request, clear_index={clear_index}", extra={"query_id": query_id, "conversation_id": "N/A"})
    file_paths = []
    try:
        if clear_index and len(files) == 0:
            logger.debug("Attempting to delete and recreate Pinecone index", extra={"query_id": query_id, "conversation_id": "N/A"})
            try:
                delete_and_recreate_index()
                logger.info("Index deleted and recreated successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"message": "Index deleted and recreated successfully!"})
            except Exception as e:
                logger.error(f"Failed to delete and recreate index: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"error": "Failed to reset the index. Please try again."}, status_code=500)
        
        if len(files) == 0:
            logger.warning("No files provided", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({"error": "No files provided. Please upload at least one PDF or TXT file."}, status_code=400)
        
        # Validate file extensions
        valid_extensions = {'.pdf', '.txt'}
        invalid_files = [f.filename for f in files if not any(f.filename.lower().endswith(ext) for ext in valid_extensions)]
        if invalid_files:
            logger.warning(f"Invalid file extensions: {invalid_files}", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({
                "error": f"Invalid file(s) detected: {', '.join(invalid_files)}. Only PDF and TXT files are supported."
            }, status_code=400)

        file_names = [f.filename for f in files]
        logger.info(f"Processing files: {file_names}", extra={"query_id": query_id, "conversation_id": "N/A"})
        
        for file in files:
            logger.debug(f"Saving file: {file.filename}", extra={"query_id": query_id, "conversation_id": "N/A"})
            temp_path = f"temp_{file.filename}"
            try:
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                file_paths.append(temp_path)
            except Exception as e:
                logger.error(f"Failed to save file {file.filename}: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                raise
        
        logger.debug("Calling process_and_save_files", extra={"query_id": query_id, "conversation_id": "N/A"})
        try:
            process_and_save_files(file_paths, clear_index=clear_index)
            logger.info("Files processed successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
        except Exception as e:
            logger.error(f"Failed to process files: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
            raise
        
        for path in file_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up temp file: {path}", extra={"query_id": query_id, "conversation_id": "N/A"})
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {path}: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        
        return JSONResponse({"message": "Files processed and vectors added to the index successfully!"})
    
    except Exception as e:
        for path in file_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up temp file on error: {path}", extra={"query_id": query_id, "conversation_id": "N/A"})
                except Exception as e_cleanup:
                    logger.warning(f"Failed to clean up temp file {path} on error: {str(e_cleanup)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        logger.error(f"Error processing files: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to process files. Please check your files and try again."}, status_code=500)

'''

@router.post("/upload_files")
async def upload_files(files: List[UploadFile] = File([]), clear_index: bool = Form(False)):
    query_id = str(uuid.uuid4())
    logger.info(f"Received file upload request, clear_index={clear_index}", extra={"query_id": query_id, "conversation_id": "N/A"})
    
    temp_paths: List[str] = []
    conv_id = str(uuid.uuid4())  # One conversation ID for all files in this upload
    data_saved = False

    try:
        # --- 1. Handle clear_index with no files ---
        if clear_index and len(files) == 0:
            logger.debug("Attempting to delete and recreate Pinecone index", extra={"query_id": query_id, "conversation_id": "N/A"})
            try:
                delete_and_recreate_index()
                logger.info("Index deleted and recreated successfully", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"message": "Index deleted and recreated successfully!"})
            except Exception as e:
                logger.error(f"Failed to delete and recreate index: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                return JSONResponse({"error": "Failed to reset the index. Please try again."}, status_code=500)

        # --- 2. No files provided ---
        if len(files) == 0:
            logger.warning("No files provided", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({"error": "No files provided. Please upload at least one file."}, status_code=400)

        # --- 3. Validate file extensions ---
        VALID_EXTENSIONS = {'.pdf', '.txt', '.csv', '.xlsx', '.xls'}
        invalid_files = [
            f.filename for f in files
            if not any(f.filename.lower().endswith(ext) for ext in VALID_EXTENSIONS)
        ]
        if invalid_files:
            logger.warning(f"Invalid file extensions: {invalid_files}", extra={"query_id": query_id, "conversation_id": "N/A"})
            return JSONResponse({
                "error": f"Invalid file(s): {', '.join(invalid_files)}. "
                         "Only PDF, TXT, CSV, XLSX, XLS files are supported."
            }, status_code=400)

        # --- 4. Process each file ---
        for file in files:
            ext = os.path.splitext(file.filename)[1].lower()
            temp_path = f"temp_{uuid.uuid4()}_{file.filename}"
            temp_paths.append(temp_path)

            try:
                # Save uploaded file
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # --- CSV / XLSX → Save as separate JSON file in conversation folder ---
                if ext == ".csv":
                    df = pd.read_csv(temp_path)
                    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in os.path.splitext(file.filename)[0])
                    _save_df(df, conv_id, safe_name)  # Uses new _save_df with filename
                    logger.debug(f"Saved CSV as JSON: {file.filename} → {safe_name}.json ({len(df)} rows)", 
                                extra={"query_id": query_id, "conversation_id": conv_id})
                    data_saved = True

                elif ext in {".xlsx", ".xls"}:
                    df = pd.read_excel(temp_path)
                    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in os.path.splitext(file.filename)[0])
                    _save_df(df, conv_id, safe_name)
                    logger.debug(f"Saved XLSX as JSON: {file.filename} → {safe_name}.json ({len(df)} rows)", 
                                extra={"query_id": query_id, "conversation_id": conv_id})
                    data_saved = True

                else:
                    # --- PDF / TXT → RAG (Pinecone) ---
                    process_and_save_files([temp_path], clear_index=False)
                    logger.debug(f"Sent to RAG: {file.filename}", extra={"query_id": query_id, "conversation_id": "N/A"})

            except Exception as e:
                logger.error(f"Failed to process {file.filename}: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
                raise

        # --- 5. Cleanup temp files ---
        for path in temp_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up temp file: {path}", extra={"query_id": query_id, "conversation_id": "N/A"})
                except Exception as e:
                    logger.warning(f"Failed to clean up {path}: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})

        # --- 6. Return conversation_id ---
        return JSONResponse({
            "message": "Files processed successfully! CSV/XLSX saved as separate JSON files.",
            "conversation_id": conv_id,
            "data_uploaded": data_saved
        })

    except Exception as e:
        # --- 7. Emergency cleanup ---
        for path in temp_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        logger.error(f"Error processing files: {str(e)}", extra={"query_id": query_id, "conversation_id": "N/A"})
        return JSONResponse({"error": "Failed to process files. Please try again."}, status_code=500)



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
                return JSONResponse({"error": "Failed to reset the index. Please try again."}, status_code=500)
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
    conv_id = req.conversation_id or str(uuid.uuid4())
    logger.info(f"Question: {req.question}", extra={"query_id": query_id, "conversation_id": conv_id})

    if not req.question.strip():
        return JSONResponse({"error": "Empty question."}, status_code=400)

    # CLASSIFY: DATA or RAG
    kind = classify_query(req.question)
    logger.info(f"Classifier → {kind}", extra={"query_id": query_id, "conversation_id": conv_id})

    try:
        if kind == "DATA":
            resp = answer_data_query(req.question, conv_id)
        else:
            resp = answer_rag(req.question, conv_id)
        return JSONResponse(resp)
    except Exception as e:
        logger.error(f"Ask error: {str(e)}", extra={"query_id": query_id, "conversation_id": conv_id})
        return JSONResponse({"error": "Failed to process question."}, status_code=500)





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
        return JSONResponse({"error": "Failed to clear the index. Please try again."}, status_code=500)