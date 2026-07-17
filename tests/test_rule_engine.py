"""Unit tests for rule engine billing error detection."""

from datetime import date
from decimal import Decimal

import pytest

from schemas import ExtractedFields, DocumentType, ErrorType, ConfidenceLevel
from pipeline.rule_engine import (
    check_duplicate_charges,
    check_unbundling_violations,
    check_balance_billing_violations,
    check_medical_necessity_denial_weakness,
    check_out_of_network_coding_error,
    run_all_rule_checks,
)


class TestDuplicateCharges:
    """Test duplicate charge detection."""
    
    def test_detects_duplicate_cpt_codes(self):
        """Should detect when same CPT code appears multiple times."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285", "70450", "99285"],  # 99285 appears twice
            service_date=date(2024, 3, 15),
        )
        
        findings = check_duplicate_charges(fields)
        
        assert len(findings) == 1
        assert findings[0].error_type == ErrorType.DUPLICATE_CHARGE
        assert findings[0].confidence == ConfidenceLevel.HIGH
        assert "99285" in findings[0].description
    
    def test_no_duplicates_when_all_unique(self):
        """Should return empty list when no duplicates."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285", "70450", "80053"],
            service_date=date(2024, 3, 15),
        )
        
        findings = check_duplicate_charges(fields)
        
        assert len(findings) == 0
    
    def test_skips_check_when_no_service_date(self):
        """Should skip check if service date is missing."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285", "99285"],
            service_date=None,
        )
        
        findings = check_duplicate_charges(fields)
        
        assert len(findings) == 0


class TestUnbundlingViolations:
    """Test unbundling violation detection."""
    
    def test_detects_ct_head_bundling_violation(self):
        """Should detect CT head with and without contrast billed separately."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["70450", "70460"],  # Both CT head codes
            service_date=date(2024, 3, 15),
        )
        
        findings = check_unbundling_violations(fields)
        
        assert len(findings) == 1
        assert findings[0].error_type == ErrorType.UNBUNDLING_VIOLATION
        assert findings[0].confidence == ConfidenceLevel.HIGH
        assert "70450" in findings[0].evidence[0]
        assert "70460" in findings[0].evidence[0]
    
    def test_detects_em_level_bundling_violation(self):
        """Should detect multiple E&M visit levels billed for same encounter."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99213", "99214"],
            service_date=date(2024, 3, 15),
        )
        
        findings = check_unbundling_violations(fields)
        
        assert len(findings) == 1
        assert findings[0].error_type == ErrorType.UNBUNDLING_VIOLATION
    
    def test_no_violations_when_codes_not_bundled(self):
        """Should return empty when codes don't violate bundling rules."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285", "70450"],  # ER visit + CT scan - NOT bundled
            service_date=date(2024, 3, 15),
        )
        
        findings = check_unbundling_violations(fields)
        
        assert len(findings) == 0


class TestBalanceBillingViolations:
    """Test No Surprises Act balance billing detection."""
    
    def test_detects_emergency_service_balance_billing(self):
        """Should flag potential NSA violation for emergency services with patient balance."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285"],  # Emergency dept visit
            patient_responsibility=Decimal("2100.00"),
            in_network=False,  # Out of network
            service_date=date(2024, 3, 15),
        )
        
        findings = check_balance_billing_violations(fields)
        
        assert len(findings) == 1
        assert findings[0].error_type == ErrorType.NO_SURPRISES_ACT_VIOLATION
        assert "Emergency" in findings[0].description
        assert "No Surprises Act" in findings[0].legal_citation
    
    def test_flags_oon_provider_for_investigation(self):
        """Should flag OON non-emergency service for NSA investigation."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["27447"],  # Knee replacement - non-emergency
            in_network=False,
            service_date=date(2024, 3, 15),
        )
        
        findings = check_balance_billing_violations(fields)
        
        assert len(findings) == 1
        assert findings[0].confidence == ConfidenceLevel.LOW
        assert "in-network facility" in findings[0].description.lower()
    
    def test_no_violation_when_network_status_unknown(self):
        """Should skip check when network status is unknown."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285"],
            in_network=None,  # Unknown
        )
        
        findings = check_balance_billing_violations(fields)
        
        assert len(findings) == 0


class TestMedicalNecessityDenials:
    """Test medical necessity denial analysis."""
    
    def test_high_confidence_for_emergency_med_necessity_denial(self):
        """CO-50 denial on emergency service = HIGH confidence appeal case."""
        fields = ExtractedFields(
            document_type=DocumentType.DENIAL_LETTER,
            cpt_codes=["99285", "70450"],  # ER visit + CT
            denial_reason_code="CO-50",
            patient_responsibility=Decimal("2100.00"),
            service_date=date(2024, 3, 15),
        )
        
        findings = check_medical_necessity_denial_weakness(fields)
        
        assert len(findings) == 1
        assert findings[0].error_type == ErrorType.MEDICAL_NECESSITY_DISPUTE
        assert findings[0].confidence == ConfidenceLevel.HIGH
        assert "prudent layperson" in findings[0].description.lower()
        assert "EMTALA" in findings[0].legal_citation
    
    def test_medium_confidence_for_imaging_med_necessity_denial(self):
        """CO-50 denial on diagnostic imaging = MEDIUM confidence (provider can document)."""
        fields = ExtractedFields(
            document_type=DocumentType.DENIAL_LETTER,
            cpt_codes=["70450"],  # CT scan
            denial_reason_code="CO-50",
            patient_responsibility=Decimal("1500.00"),
            service_date=date(2024, 3, 15),
        )
        
        findings = check_medical_necessity_denial_weakness(fields)
        
        assert len(findings) == 1
        assert findings[0].confidence == ConfidenceLevel.MEDIUM
        assert "diagnostic imaging" in findings[0].description.lower()
    
    def test_ignores_non_co50_denials(self):
        """Should only check CO-50 denials."""
        fields = ExtractedFields(
            document_type=DocumentType.DENIAL_LETTER,
            cpt_codes=["99285"],
            denial_reason_code="CO-11",  # Different denial code
            service_date=date(2024, 3, 15),
        )
        
        findings = check_medical_necessity_denial_weakness(fields)
        
        assert len(findings) == 0


class TestOutOfNetworkCodingError:
    """Test OON miscoding detection."""
    
    def test_flags_oon_with_denial_code(self):
        """Should flag OON + certain denial codes for verification."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            in_network=False,
            denial_reason_code="CO-96",  # Non-covered charge
        )
        
        findings = check_out_of_network_coding_error(fields)
        
        assert len(findings) == 1
        assert findings[0].error_type == ErrorType.OUT_OF_NETWORK_MISCODING
        assert findings[0].confidence == ConfidenceLevel.MEDIUM
    
    def test_no_flag_when_in_network(self):
        """Should not flag in-network claims."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            in_network=True,
            denial_reason_code="CO-96",
        )
        
        findings = check_out_of_network_coding_error(fields)
        
        assert len(findings) == 0


class TestRunAllRuleChecks:
    """Test the combined rule engine."""
    
    def test_runs_all_checks_and_sorts_by_confidence(self):
        """Should run all checks and sort findings by confidence."""
        fields = ExtractedFields(
            document_type=DocumentType.DENIAL_LETTER,
            cpt_codes=["99285", "70450"],
            denial_reason_code="CO-50",
            patient_responsibility=Decimal("2100.00"),
            in_network=True,
            service_date=date(2024, 3, 15),
        )
        
        findings = run_all_rule_checks(fields)
        
        # Should have at least the emergency med necessity finding
        assert len(findings) > 0
        
        # Should be sorted by confidence (HIGH first)
        if len(findings) > 1:
            confidences = [f.confidence for f in findings]
            confidence_order = [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW, ConfidenceLevel.SPECULATIVE]
            for i in range(len(confidences) - 1):
                curr_idx = confidence_order.index(confidences[i])
                next_idx = confidence_order.index(confidences[i + 1])
                assert curr_idx <= next_idx, "Findings should be sorted by confidence"
    
    def test_complex_case_with_multiple_violations(self):
        """Test a complex case with multiple detectable issues."""
        fields = ExtractedFields(
            document_type=DocumentType.EOB,
            cpt_codes=["99285", "99285", "70450", "70460"],  # Duplicate + unbundling
            denial_reason_code="CO-50",
            patient_responsibility=Decimal("3000.00"),
            in_network=True,
            service_date=date(2024, 3, 15),
        )
        
        findings = run_all_rule_checks(fields)
        
        # Should detect multiple issues
        assert len(findings) >= 3
        
        # Should have duplicate, unbundling, and med necessity findings
        error_types = {f.error_type for f in findings}
        assert ErrorType.DUPLICATE_CHARGE in error_types
        assert ErrorType.UNBUNDLING_VIOLATION in error_types
        assert ErrorType.MEDICAL_NECESSITY_DISPUTE in error_types
