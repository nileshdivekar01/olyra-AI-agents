from fastapi import APIRouter, UploadFile, File
import tempfile
from .services.pinecone_store import store_pdf_to_pinecone
from app.services.scheduler import schedule_production
from app.schema.upload import UploadResponse , ScheduleRequest
from pydantic import BaseModel
from fastapi import Body



router = APIRouter()

@router.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF → Embed with Gemini → Store in Pinecone"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        result = store_pdf_to_pinecone(tmp_path)
        return UploadResponse(message="PDF stored successfully in Pinecone", details=result)
    except Exception as e:
        return UploadResponse(message="Error", details={"error": str(e)})
    

@router.post("/schedule")
async def create_schedule(req:ScheduleRequest):
  
    result = schedule_production(req.query)
    return result