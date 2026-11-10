import io
import pytest
from datetime import date
from pypdf import PdfReader
from app.models.base import db
from app.models.auth import User, Role
from app.models.organization import Organization, OrganizationUser
from app.models.regulatory import RegulatoryRequirement
from app.models.scoring import ScoringPolicyVersion
from app.models.assessment import ComplianceAssessment, AssessmentResponse, AssessmentEvidence
from app.models.compliance_management import ComplianceGap
from app.services.scoring_service import ScoringEngine
from app.services.reporting_service import ReportingService
from app.services.pdf_evidence_generator import (
    generate_kra_tax_compliance_cert,
    generate_odpc_registration_cert,
    generate_wiba_policy_schedule,
    generate_osha_inspection_report,
    generate_etims_signoff_cert,
)


def test_statutory_evidence_pdf_generators():
    """Validates that all 5 statutory evidence generators produce non-blank, rich PDFs with readable text."""
    generators = [
        ("KRA Tax Compliance", generate_kra_tax_compliance_cert("Apex Logistics Solutions Ltd", "P051992233M")),
        ("ODPC Registration", generate_odpc_registration_cert("Apex Logistics Solutions Ltd", "P051992233M")),
        ("WIBA Policy Schedule", generate_wiba_policy_schedule("Apex Logistics Solutions Ltd", 45)),
        ("OSHA Inspection Report", generate_osha_inspection_report("Apex Logistics Solutions Ltd", "Nairobi")),
        ("eTIMS Integration Signoff", generate_etims_signoff_cert("Apex Logistics Solutions Ltd", "P051992233M")),
    ]

    for name, pdf_bytes in generators:
        assert pdf_bytes is not None, f"{name} returned None"
        assert len(pdf_bytes) > 2000, f"{name} byte size too small: {len(pdf_bytes)}"
        assert pdf_bytes.startswith(b"%PDF"), f"{name} is not a valid PDF stream"

        # Verify PDF contains real extracted text (not blank)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1, f"{name} has 0 pages"
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert len(text.strip()) > 300, f"{name} has insufficient extracted text ({len(text)} chars); appears blank!"
        assert "Apex Logistics Solutions Ltd" in text or "KENYA" in text


def test_pdf_report_and_certificate_generation(app):
    """Validates full Executive Audit PDF, Certificate PDF, and Gaps PDF generation."""
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization(
            name="Report Test SME Ltd",
            business_registration_number="REG-REP-01",
            kra_pin="PIN-REP-01",
            contact_email="rep@test.ke",
            county="Nairobi",
        )
        user = User(email="rep_user@test.ke", full_name="Report Tester")
        user.set_password("RepPass123!")
        db.session.add_all([org, user])
        db.session.flush()

        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=user.id,
            scoring_policy_version_id=version.id,
            title="Q1 Comprehensive Audit",
            assessment_period="2026 Q1",
            assessment_date=date.today(),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment)
        db.session.flush()

        # Fill all requirements
        all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).all()
        for idx, req in enumerate(all_reqs):
            val = AssessmentResponse.RESPONSE_COMPLIANT if idx % 4 != 0 else AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req.id,
                response_value=val,
                notes=f"Audited observation for {req.code}",
                updated_by_id=user.id,
            )
            db.session.add(resp)
        db.session.commit()

        ScoringEngine.apply_and_persist_scores(assessment, version)

        # 1. Generate Executive Audit PDF report
        pdf_buffer = ReportingService.generate_assessment_pdf(assessment)
        assert pdf_buffer is not None
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 5000
        assert pdf_bytes.startswith(b"%PDF")

        # Verify Executive Audit PDF contains text across all evaluated requirements
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 2, "Comprehensive report should be multi-page"
        full_text = "".join(p.extract_text() or "" for p in reader.pages)
        assert "Report Test SME Ltd" in full_text
        assert "PIN-REP-01" in full_text
        assert "Statutory Obligations Audit Register" in full_text
        assert "Page 1 of" in full_text

        # 2. Generate Landscape Compliance Certificate
        cert_buffer = ReportingService.generate_compliance_certificate_pdf(assessment)
        assert cert_buffer is not None
        cert_bytes = cert_buffer.getvalue()
        assert len(cert_bytes) > 2000
        assert cert_bytes.startswith(b"%PDF")
        cert_reader = PdfReader(io.BytesIO(cert_bytes))
        cert_text = "".join(p.extract_text() or "" for p in cert_reader.pages)
        assert "CERTIFICATE OF REGULATORY COMPLIANCE" in cert_text
        assert "REPORT TEST SME LTD" in cert_text.upper()

        # 3. Generate Gaps Matrix PDF
        gaps_buffer = ReportingService.generate_gaps_pdf(org.id)
        assert gaps_buffer is not None
        gaps_bytes = gaps_buffer.getvalue()
        assert len(gaps_bytes) > 2000
        assert gaps_bytes.startswith(b"%PDF")
        gaps_reader = PdfReader(io.BytesIO(gaps_bytes))
        gaps_text = "".join(p.extract_text() or "" for p in gaps_reader.pages)
        assert "Statutory Gaps & Remediation Exposure Matrix" in gaps_text
        assert "Report Test SME Ltd" in gaps_text

        # 4. Generate CSV
        csv_str = ReportingService.generate_assessment_csv(assessment)
        assert "CRAS - COMPLIANCE ASSESSMENT EXPORT" in csv_str
        assert "Report Test SME Ltd" in csv_str
        assert "PIN-REP-01" in csv_str

        # 5. Generate Excel
        excel_stream = ReportingService.generate_excel_export(assessment)
        assert excel_stream is not None
        excel_bytes = excel_stream.getvalue()
        assert len(excel_bytes) > 1000
