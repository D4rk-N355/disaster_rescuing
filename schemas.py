from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- Input Schemas ---
class Location(BaseModel):
    lat: float
    lng: float

class Metadata(BaseModel):
    incident_id: str
    priority_weighting: Literal["balanced", "speed", "expertise"]

class WorkType(BaseModel):
    type_id: str
    required_skills: List[str]

class Volunteer(BaseModel):
    id: str
    skills: List[str]
    location: Location
    availability: bool

class Task(BaseModel):
    id: str
    type_id: str
    location: Location
    urgency: int = Field(..., ge=1, le=5)

class DispatchRequest(BaseModel):
    metadata: Metadata
    work_types: List[WorkType]
    volunteers: List[Volunteer]
    tasks: List[Task]

# --- Output Schemas ---
class Assignment(BaseModel):
    task_id: str
    assigned_volunteers: List[str]
    eta_minutes: int
    reasoning_summary: str

class DispatchResponse(BaseModel):
    status: str
    dispatch_id: str
    assignments: List[Assignment]