"""Deterministic rule-based billing error detection.

This module contains ZERO LLM calls — pure Python logic for detecting
common billing errors and No Surprises Act violations.
"""

from decimal import Decimal
from typing import Optional

from schemas import ErrorFinding, ErrorType, ConfidenceLevel, ExtractedFields


# Known CPT code bundling rules (simplified subset for demo)
# In production, this would be a full database of NCCI (National Correct Coding Initiative) edits
CPT_BUNDLING_RULES = {
    # CT scans: can't bill both with and without contrast on same day for same body part
    ("70450", "70460"): "CT head with and without contrast cannot be billed separately",
    ("70450", "70470"): "CT head with and without contrast cannot be billed separately",
    
    # E&M codes: can't bill multiple E&M visits on same day by same provider
    ("99213", "99214"): "Cannot bill multiple E&M levels for same encounter",
    ("99284", "99285"): "Cannot bill multiple ER visit levels for same encounter",
    
    # Lab panels include individual tests
    ("80053", "84443"): "Comprehensive metabolic panel (80053) includes TSH (84443)",
    ("80053", "82247"): "Comprehensive metabolic panel includes bilirubin",
}


# Common denial reason codes and their meanings
DENIAL_CODES = {
    "CO-11": "Diagnosis inconsistent with procedure",
    "CO-16": "Claim lacks information or has submission/billing error",
    "CO-50": "Non-covered service / Not medically necessary",
    "CO-96": "Non-covered charge(s)",
    "CO-97": "Benefit maximum reached",
    "CO-109": "Not covered unless specific criteria met",
    "CO-167": "Not covered based on place of service",
    "CO-197": "Precertification/authorization missing",
    "CO-213": "Duplicate charge",
}


def check_duplicate_charges(fields: ExtractedFields) -> list[ErrorFinding]:
    """Detect duplicate CPT codes billed on the same date of service.
    
    This is a HIGH confidence check when found — billing the same procedure
    code multiple times on the same day is usually an error unless explicitly
    documented as multiple units.
    """
    findings = []
    
    if not fields.cpt_codes or not fields.service_date:
        return findings
    
    # Check for exact duplicates
    seen_codes = set()
    for code in fields.cpt_codes:
        if code in seen_codes:
            findings.append(ErrorFinding(
                error_type=ErrorType.DUPLICATE_CHARGE,
                confidence=ConfidenceLevel.HIGH,
                description=f"CPT code {code} appears multiple times for the same date of service ({fields.service_date}). Unless explicitly documented as multiple units, this is likely a duplicate billing error.",
                evidence=[
                    f"CPT {code} appears {fields.cpt_codes.count(code)} times",
                    f"Service date: {fields.service_date}",
                ],
                legal_citation="Medicare Claims Processing Manual Ch. 23 §20.7.3: Duplicate claims are claims submitted multiple times for the same service.",
                estimated_impact=None,  # Would need line-item amounts to calculate
                recommendation="Request itemized bill breakdown. If confirmed duplicate, dispute under insurer's duplicate payment recovery process.",
            ))
            # Only report once per code
            break
        seen_codes.add(code)
    
    return findings


def check_unbundling_violations(fields: ExtractedFields) -> list[ErrorFinding]:
    """Detect CPT code unbundling (billing separately for bundled services).
    
    Unbundling = charging separately for services that should be billed together
    under a single comprehensive code. This inflates charges.
    """
    findings = []
    
    if not fields.cpt_codes:
        return findings
    
    # Check all pairs of codes against bundling rules
    codes_set = set(fields.cpt_codes)
    
    for (code1, code2), violation_msg in CPT_BUNDLING_RULES.items():
        if code1 in codes_set and code2 in codes_set:
            findings.append(ErrorFinding(
                error_type=ErrorType.UNBUNDLING_VIOLATION,
                confidence=ConfidenceLevel.HIGH,
                description=f"Unbundling violation detected: {violation_msg}",
                evidence=[
                    f"Both CPT {code1} and {code2} billed on same date",
                    f"Service date: {fields.service_date}",
                    violation_msg,
                ],
                legal_citation="NCCI (National Correct Coding Initiative) edits: CMS publishes code pair edits that identify services that should not be billed together.",
                estimated_impact=None,
                recommendation="Challenge the separate billing. Request rebilling under the appropriate comprehensive code.",
            ))
    
    return findings


def check_balance_billing_violations(fields: ExtractedFields) -> list[ErrorFinding]:
    """Detect No Surprises Act balance billing violations.
    
    The No Surprises Act (effective Jan 1, 2022) prohibits balance billing for:
    1. Emergency services (regardless of network status)
    2. Non-emergency services at in-network facilities by out-of-network providers
       (unless patient gives advance consent)
    
    This is enforceable and has teeth — violations can be reported to CMS.
    """
    findings = []
    
    # Need certain fields to make this determination
    if fields.in_network is None:
        return findings
    
    # Check for emergency service balance billing (violation regardless of network status)
    is_emergency_service = _is_emergency_cpt_code(fields.cpt_codes)
    
    if is_emergency_service:
        # If patient has any balance beyond their plan's in-network cost-sharing,
        # that's potentially a violation
        if fields.patient_responsibility and fields.patient_responsibility > 0:
            findings.append(ErrorFinding(
                error_type=ErrorType.NO_SURPRISES_ACT_VIOLATION,
                confidence=ConfidenceLevel.MEDIUM,  # Medium because we don't know deductible/copay details
                description="Potential No Surprises Act violation: Emergency services must be billed at in-network rates regardless of provider network status. Patient cannot be balance-billed beyond in-network cost-sharing.",
                evidence=[
                    "Emergency service detected (ER visit codes present)",
                    f"Patient responsibility: ${fields.patient_responsibility}",
                    "No Surprises Act covers all emergency services",
                ],
                legal_citation="No Surprises Act § 2799B-1(b) & § 2799B-2(a): Emergency services must be covered without regard to network status, and providers cannot balance bill.",
                estimated_impact=fields.patient_responsibility if fields.patient_responsibility else None,
                recommendation="Verify that patient responsibility amount reflects only in-network cost-sharing (deductible/copay/coinsurance). If provider is billing beyond that, cite No Surprises Act and demand re-billing at in-network rate.",
            ))
    
    # Check for out-of-network provider at in-network facility (non-emergency)
    elif fields.in_network is False and not is_emergency_service:
        # This is trickier — violation only if:
        # 1. Service was at an in-network facility, AND
        # 2. Patient didn't give advance written consent
        # We can flag it as something to investigate
        findings.append(ErrorFinding(
            error_type=ErrorType.NO_SURPRISES_ACT_VIOLATION,
            confidence=ConfidenceLevel.LOW,  # Low confidence without facility network status
            description="Possible No Surprises Act violation: If this out-of-network service was provided at an in-network facility without advance written consent, you cannot be balance-billed.",
            evidence=[
                "Provider marked as out-of-network",
                "Service appears to be non-emergency",
            ],
            legal_citation="No Surprises Act § 2799B-2(b): Out-of-network providers at in-network facilities cannot balance bill without advance consent notice.",
            estimated_impact=None,
            recommendation="Determine if the service was provided at an in-network facility. If yes, and you did not sign an advance consent form, this is a violation. File a complaint with CMS No Surprises Help Desk.",
        ))
    
    return findings


def check_medical_necessity_denial_weakness(fields: ExtractedFields) -> list[ErrorFinding]:
    """Check if a 'not medically necessary' denial is potentially weak/appealable.
    
    This is NOT purely deterministic — we're looking for patterns that suggest
    the denial is incorrect based on commonly accepted standards.
    
    CO-50 denials are THE most common and THE most overturned on appeal.
    """
    findings = []
    
    if fields.denial_reason_code != "CO-50":
        return findings
    
    # Emergency service + medical necessity denial = very strong appeal case
    is_emergency = _is_emergency_cpt_code(fields.cpt_codes)
    if is_emergency:
        findings.append(ErrorFinding(
            error_type=ErrorType.MEDICAL_NECESSITY_DISPUTE,
            confidence=ConfidenceLevel.HIGH,
            description="Medical necessity denial for emergency service. Emergency services must be covered based on 'prudent layperson' standard (symptoms that would lead a reasonable person to believe they need emergency care), NOT retrospective medical necessity determination.",
            evidence=[
                f"Denial code: {fields.denial_reason_code} ({DENIAL_CODES.get(fields.denial_reason_code, 'unknown')})",
                "Emergency service codes detected",
                "Prudent layperson standard applies",
            ],
            legal_citation="EMTALA § 1867(e)(1)(B) & ACA § 2719A: Emergency services covered based on presenting symptoms, not final diagnosis. No prior authorization can be required.",
            estimated_impact=fields.patient_responsibility,
            recommendation="File appeal immediately. Cite prudent layperson standard. Attach: ER admission notes showing presenting symptoms, triage assessment, physician clinical decision-making.",
        ))
    
    # Diagnostic imaging + medical necessity denial = medium appeal case
    # (These are frequently overturned if provider documents clinical reasoning)
    elif _is_diagnostic_imaging(fields.cpt_codes):
        findings.append(ErrorFinding(
            error_type=ErrorType.MEDICAL_NECESSITY_DISPUTE,
            confidence=ConfidenceLevel.MEDIUM,
            description="Medical necessity denial for diagnostic imaging. These denials are frequently overturned when physician provides clinical documentation supporting the order.",
            evidence=[
                f"Denial code: {fields.denial_reason_code}",
                "Diagnostic imaging codes present (CT/MRI/X-ray)",
            ],
            legal_citation=None,
            estimated_impact=fields.patient_responsibility,
            recommendation="Request peer-to-peer review. Have ordering physician provide clinical notes explaining why imaging was necessary based on patient presentation, symptoms, and differential diagnosis.",
        ))
    
    return findings


def check_out_of_network_coding_error(fields: ExtractedFields) -> list[ErrorFinding]:
    """Check for potential out-of-network miscoding.
    
    Common error: Insurer incorrectly processes in-network claim as out-of-network,
    resulting in lower payment and higher patient responsibility.
    """
    findings = []
    
    # We can only flag this if we have evidence it SHOULD be in-network
    # For now, just flag when in_network=False as something to verify
    if fields.in_network is False and fields.denial_reason_code in ["CO-96", "CO-167"]:
        findings.append(ErrorFinding(
            error_type=ErrorType.OUT_OF_NETWORK_MISCODING,
            confidence=ConfidenceLevel.MEDIUM,
            description="Service processed as out-of-network. Verify that the provider was actually out-of-network at the time of service — network status errors are common and result in underpayment.",
            evidence=[
                "Claim processed as out-of-network",
                f"Denial/reduction code: {fields.denial_reason_code}",
            ],
            legal_citation=None,
            estimated_impact=None,
            recommendation="Check insurer's online provider directory for the service date. If provider was in-network, request reprocessing. Insurers must honor their published directories under 'network adequacy' rules.",
        ))
    
    return findings


# Helper functions

def _is_emergency_cpt_code(cpt_codes: list[str]) -> bool:
    """Check if any codes indicate emergency department service."""
    emergency_codes = {
        "99281", "99282", "99283", "99284", "99285",  # ER visit E&M codes
    }
    return any(code in emergency_codes for code in cpt_codes)


def _is_diagnostic_imaging(cpt_codes: list[str]) -> bool:
    """Check if any codes are diagnostic imaging (CT, MRI, X-ray)."""
    # Simplified check: codes starting with 70-79 are typically radiology
    return any(code.startswith(("70", "71", "72", "73", "74", "75", "76", "77", "78", "79")) 
               for code in cpt_codes)


def run_all_rule_checks(fields: ExtractedFields) -> list[ErrorFinding]:
    """Run all deterministic rule checks and return combined findings.
    
    This is the main entry point for the rule engine.
    Each check is independent and returns 0+ findings.
    """
    all_findings = []
    
    # Run each check
    all_findings.extend(check_duplicate_charges(fields))
    all_findings.extend(check_unbundling_violations(fields))
    all_findings.extend(check_balance_billing_violations(fields))
    all_findings.extend(check_medical_necessity_denial_weakness(fields))
    all_findings.extend(check_out_of_network_coding_error(fields))
    
    # Sort by confidence (high first) then impact
    all_findings.sort(
        key=lambda f: (
            ["high", "medium", "low", "speculative"].index(f.confidence.value),
            -(f.estimated_impact or Decimal(0))
        )
    )
    
    return all_findings
