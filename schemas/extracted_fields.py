"""Schema for structured fields extracted from medical documents."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Type of medical billing document."""

    EOB = "eob"  # Explanation of Benefits
    DENIAL_LETTER = "denial_letter"
    ITEMIZED_BILL = "itemized_bill"
    UNKNOWN = "unknown"


class ExtractedFields(BaseModel):
    """Structured fields extracted from a medical billing document.
    
    This represents the normalized data pulled from an EOB, denial letter,
    or itemized bill after OCR/text extraction and LLM parsing.
    """

    document_type: DocumentType = Field(
        description="Classified document type"
    )
    
    # Patient information
    patient_name: Optional[str] = Field(
        default=None,
        description="Full name of the patient"
    )
    patient_id: Optional[str] = Field(
        default=None,
        description="Patient or member ID from insurer"
    )
    
    # Provider/insurer information
    insurer_name: Optional[str] = Field(
        default=None,
        description="Name of the insurance company"
    )
    provider_name: Optional[str] = Field(
        default=None,
        description="Name of the healthcare provider/facility"
    )
    
    # Service details
    service_date: Optional[date] = Field(
        default=None,
        description="Date of service (or start date if range)"
    )
    service_date_end: Optional[date] = Field(
        default=None,
        description="End date of service if a range"
    )
    
    # Medical codes
    cpt_codes: list[str] = Field(
        default_factory=list,
        description="List of CPT (Current Procedural Terminology) codes"
    )
    icd_codes: list[str] = Field(
        default_factory=list,
        description="List of ICD (diagnosis) codes"
    )
    
    # Financial details
    billed_amount: Optional[Decimal] = Field(
        default=None,
        description="Total amount billed by provider"
    )
    allowed_amount: Optional[Decimal] = Field(
        default=None,
        description="Amount allowed by insurance (negotiated rate)"
    )
    paid_amount: Optional[Decimal] = Field(
        default=None,
        description="Amount actually paid by insurance"
    )
    patient_responsibility: Optional[Decimal] = Field(
        default=None,
        description="Amount patient is expected to pay"
    )
    
    # Denial information
    denial_reason_code: Optional[str] = Field(
        default=None,
        description="Insurance denial reason code (e.g., CO-11, CO-16, CO-50)"
    )
    denial_reason_text: Optional[str] = Field(
        default=None,
        description="Human-readable denial reason from the document"
    )
    
    # Network status
    in_network: Optional[bool] = Field(
        default=None,
        description="Whether the provider was in-network"
    )
    
    # Raw text context for reference
    raw_denial_context: Optional[str] = Field(
        default=None,
        description="Raw text snippet around the denial explanation for context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "denial_letter",
                "patient_name": "Jane Doe",
                "patient_id": "MEM123456789",
                "insurer_name": "Blue Cross Blue Shield",
                "provider_name": "City General Hospital",
                "service_date": "2024-03-15",
                "cpt_codes": ["99285", "70450"],
                "icd_codes": ["R51.9", "G43.909"],
                "billed_amount": "3500.00",
                "allowed_amount": "2100.00",
                "paid_amount": "0.00",
                "patient_responsibility": "2100.00",
                "denial_reason_code": "CO-50",
                "denial_reason_text": "Not medically necessary",
                "in_network": True,
            }
        }
