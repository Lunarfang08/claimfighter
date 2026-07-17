"""Schema for risk/error analysis report."""

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence level for a finding."""

    HIGH = "high"  # 80-100% confident
    MEDIUM = "medium"  # 50-79% confident
    LOW = "low"  # 20-49% confident
    SPECULATIVE = "speculative"  # <20% confident, worth mentioning


class ErrorType(str, Enum):
    """Types of billing/denial errors we can detect."""

    # Billing errors (deterministic rule-based detection)
    DUPLICATE_CHARGE = "duplicate_charge"
    UNBUNDLING_VIOLATION = "unbundling_violation"
    BALANCE_BILLING_VIOLATION = "balance_billing_violation"
    UPCODING = "upcoding"
    
    # Denial errors (requires policy interpretation)
    MEDICAL_NECESSITY_DISPUTE = "medical_necessity_dispute"
    INCORRECT_CODE_MAPPING = "incorrect_code_mapping"
    OUT_OF_NETWORK_MISCODING = "out_of_network_miscoding"
    TIMELY_FILING_ERROR = "timely_filing_error"
    AUTHORIZATION_ERROR = "authorization_error"
    
    # Policy/legal violations
    NO_SURPRISES_ACT_VIOLATION = "no_surprises_act_violation"
    STATE_LAW_VIOLATION = "state_law_violation"
    
    # Other
    OTHER = "other"


class ErrorFinding(BaseModel):
    """A single error or issue detected in the claim/bill."""

    error_type: ErrorType = Field(
        description="Category of error detected"
    )
    
    confidence: ConfidenceLevel = Field(
        description="How confident we are in this finding"
    )
    
    description: str = Field(
        description="Plain-English explanation of what we found"
    )
    
    evidence: list[str] = Field(
        default_factory=list,
        description="Specific evidence supporting this finding (line items, codes, dates, etc.)"
    )
    
    legal_citation: Optional[str] = Field(
        default=None,
        description="Relevant law, regulation, or policy clause (if applicable)"
    )
    
    estimated_impact: Optional[Decimal] = Field(
        default=None,
        description="Estimated dollar amount this error cost the patient (if calculable)"
    )
    
    recommendation: str = Field(
        description="What action should be taken (appeal, dispute, escalate, etc.)"
    )


class RiskReport(BaseModel):
    """Complete analysis report for a claim/bill."""

    case_summary: str = Field(
        description="One-paragraph summary of the case and what we found"
    )
    
    findings: list[ErrorFinding] = Field(
        default_factory=list,
        description="All errors/issues detected, ordered by confidence/impact"
    )
    
    total_disputed_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Total dollar amount we believe can be recovered"
    )
    
    total_billed_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Original total amount billed (for context)"
    )
    
    appeal_likelihood: ConfidenceLevel = Field(
        description="Overall likelihood of a successful appeal"
    )
    
    next_steps: list[str] = Field(
        default_factory=list,
        description="Prioritized list of actions the patient should take"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "case_summary": "Patient was billed $2,100 for emergency CT scan denied as 'not medically necessary.' However, the service was provided at an in-network facility during a true emergency (migraine with neurological symptoms), which should be covered under the No Surprises Act and the insurer's own emergency care policy.",
                "findings": [
                    {
                        "error_type": "medical_necessity_dispute",
                        "confidence": "high",
                        "description": "Emergency CT scan (CPT 70450) was denied as 'not medically necessary,' but ICD code R51.9 (headache) + G43.909 (migraine) + emergency department setting strongly indicate this was a prudent layperson emergency.",
                        "evidence": [
                            "CPT 70450: CT Head without contrast",
                            "ICD R51.9 + G43.909: Acute headache/migraine",
                            "Service location: Emergency Department",
                            "Denial code: CO-50 (not medically necessary)"
                        ],
                        "legal_citation": "No Surprises Act § 2799B-1(b): Emergency services must be covered without prior authorization, regardless of medical necessity determination after the fact.",
                        "estimated_impact": "2100.00",
                        "recommendation": "File internal appeal citing No Surprises Act and prudent layperson standard for emergency care."
                    }
                ],
                "total_disputed_amount": "2100.00",
                "total_billed_amount": "3500.00",
                "appeal_likelihood": "high",
                "next_steps": [
                    "File internal appeal with insurer within 180 days",
                    "Attach: ER admission notes, physician orders for CT scan, discharge summary",
                    "Cite: No Surprises Act emergency coverage requirements",
                    "If denied again: request external review through state insurance department"
                ]
            }
        }
