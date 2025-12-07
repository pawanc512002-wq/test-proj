# models.py
# Pydantic models + small helpers

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any


class Item(BaseModel):
    name: str
    qty: Optional[int]
    specs: Optional[Dict[str, Any]] = None


class RFPCreateRequest(BaseModel):
    text: str


class RFP(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    items: List[Item] = []
    budget: Optional[float] = None
    delivery_days: Optional[int] = None
    payment_terms: Optional[str] = None
    warranty_months: Optional[int] = None


class VendorCreate(BaseModel):
    name: str
    email: EmailStr
    contact_name: Optional[str] = None


class Vendor(BaseModel):
    id: str
    name: str
    email: EmailStr
    contact_name: Optional[str] = None
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProposalInbound(BaseModel):
    from_email: EmailStr
    subject: Optional[str] = None
    body: str


class Proposal(BaseModel):
    id: str
    rfp_id: Optional[str]
    vendor_id: str
    raw_email: Optional[str] = None
    parsed: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None
    recommendation: Optional[str] = None
