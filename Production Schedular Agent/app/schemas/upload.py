
from pydantic import BaseModel

class UploadResponse(BaseModel):
    message: str
    details: dict


class ScheduleRequest(BaseModel):
    query: str