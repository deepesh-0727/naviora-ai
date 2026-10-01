from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from decimal import Decimal

class BillingBase(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    amount: Decimal
    items: List[Dict[str, Any]]

class BillingCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    additional_items: Optional[List[Dict[str, Any]]] = None

class BillingUpdate(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None

class BillingInDBBase(BillingBase):
    id: int
    status: str
    invoice_number: str
    transaction_id: Optional[str] = None
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Billing(BillingInDBBase):
    pass

class BillingEstimateRequest(BaseModel):
    doctor_id: Optional[int] = None
    lab_test_ids: Optional[List[int]] = None
    medication_ids: Optional[List[int]] = None
    service_type: Optional[str] = "General Consultation"

class ItemDetail(BaseModel):
    name: str
    amount: float

class BillingEstimate(BaseModel):
    consultation_fee: float
    lab_fees: List[ItemDetail]
    medication_costs: List[ItemDetail]
    subtotal: float
    gst_amount: float
    total_amount: float
    currency: str = "INR"

