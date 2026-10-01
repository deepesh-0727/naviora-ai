from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    appointment_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comments: Optional[str] = None
    categories: Optional[list[str]] = None


class FeedbackResponse(BaseModel):
    id: int
    appointment_id: int
    patient_id: int
    rating: int
    comments: Optional[str] = None
    categories: Optional[list[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
