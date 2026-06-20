from pydantic import BaseModel, Field
from typing import Literal, Optional

class ClassifyRequest(BaseModel):
    complaint_text: Optional[str] = None
    text: Optional[str] = None
    ward: Optional[str] = None

class ClassifyResponse(BaseModel):
    category: Literal["Road", "Water", "Electricity", "Sanitation", "Other"]
    priority_score: int = Field(..., ge=1, le=10)
    priority_reasoning: str
    department: str
    estimated_resolution_days: int
    # Backwards compatibility fields for frontend
    reasoning: str
    resolution_days: int

class Complaint(BaseModel):
    id: str
    text: str
    category: Literal["Road", "Water", "Electricity", "Sanitation", "Other"]
    priority_score: int = Field(..., ge=1, le=10)
    department: str
    resolution_days: int
    ward: str
    lat: float
    lng: float
    timestamp: str
    status: Literal["Submitted", "In Progress", "Resolved", "SLA Breached"]

class UpdateComplaintRequest(BaseModel):
    status: Optional[Literal["Submitted", "In Progress", "Resolved", "SLA Breached"]] = None
    department: Optional[str] = None

