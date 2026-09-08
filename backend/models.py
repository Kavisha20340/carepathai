from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any, Union

class SessionState(BaseModel):
    chief_complaint: Optional[str] = None
    body_location: Optional[str] = None
    onset: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[Any] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    aggravating_factors: Optional[str] = None
    red_flags_present: List[str] = Field(default_factory=list)
    relevant_history: Optional[str] = None

class TriageRequest(BaseModel):
    transcript: str
    session_id: str
    turn_count: int
    max_turns: int = 3
    language: Optional[str] = "en"
    input_modality: Optional[Literal['voice', 'text']] = 'voice' 


class TriageResult(BaseModel):
    urgency_level: Literal['emergency', 'urgent', 'routine', 'self_care']
    specialist_type: Literal[
        'general_physician', 'orthopedic', 'dermatologist', 'pulmonologist',
        'cardiologist', 'gastroenterologist', 'ent', 'gynecologist',
        'pediatrician', 'ophthalmologist', 'psychiatrist', 'neurologist',
        'urologist', 'dentist', 'endocrinologist', 'nephrologist',
        'oncologist', 'rheumatologist', 'general_surgeon'
    ]
    confidence: Literal['high', 'moderate', 'low']
    red_flags_triggered: List[str] = []
    reasoning_summary: str

class FollowUpResponse(BaseModel):
    status: Literal['follow_up']
    updated_session_state: SessionState
    follow_up_question: str
    urgency_warning: Optional[str] = None
    denoised_transcript: Optional[str] = None

class TriageCompleteResponse(BaseModel):
    status: Literal['triage_complete']
    updated_session_state: SessionState
    triage_result: TriageResult
    urgency_warning: Optional[str] = None
    denoised_transcript: Optional[str] = None

class EmergencyResponse(BaseModel):
    status: Literal['emergency']
    message: str

class DoctorSearchRequest(BaseModel):
    specialist_type: Literal[
        'general_physician', 'orthopedic', 'dermatologist', 'pulmonologist',
        'cardiologist', 'gastroenterologist', 'ent', 'gynecologist',
        'pediatrician', 'ophthalmologist', 'psychiatrist', 'neurologist',
        'urologist', 'dentist', 'endocrinologist', 'nephrologist',
        'oncologist', 'rheumatologist', 'general_surgeon'
    ]
    lat: float
    lng: float
    radius_km: float = Field(default=10.0, ge=0.1, le=50.0)
    max_results: int = Field(default=5, ge=1, le=20)
    min_rating: float = Field(default=4.0, ge=0.0, le=5.0)
    max_rating: float = Field(default=5.0, ge=0.0, le=5.0)

class Doctor(BaseModel):
    name: str
    specialty_tag: str
    distance_km: float
    rating: float
    address: str
    phone_number: Optional[str] = None
    directions_url: str

class DoctorSearchResponse(BaseModel):
    status: str = "success"
    doctors: List[Doctor]


class TranslateResultsResponse(BaseModel):
    triage_result: TriageResult
    updated_session_state: SessionState



class SaveReportTraceRequest(BaseModel):
    session_id: str
    language: str
    report_text: str

