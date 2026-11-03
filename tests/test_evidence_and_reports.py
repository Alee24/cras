import io
import pytest
from datetime import date
from app.models.base import db
from app.models.auth import User
from app.models.organization import Organization
from app.models.regulatory import RegulatoryRequirement
from app.models.scoring import ScoringPolicyVersion
from app.models.assessment import ComplianceAssessment, AssessmentResponse
from app.services.scoring_service import ScoringEngine
from app.services.reporting_service import ReportingService


def test_pdf_report_generation(app):
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization(
            name="Report Test SME Ltd",
            business_registration_number="REG-REP-01",
            kra_pin="PIN-REP-01",
            contact_email="rep@test.ke",
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
        for req in all_reqs:
            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req.id,
                response_value=AssessmentResponse.RESPONSE_COMPLIANT,
                updated_by_id=user.id,
            )
            db.session.add(resp)
        db.session.commit()

        ScoringEngine.apply_and_persist_scores(assessment, version)

        # Generate PDF buffer
        pdf_buffer = ReportingService.generate_assessment_pdf(assessment)
        assert pdf_buffer is not None
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF")

        # Generate CSV
        csv_str = ReportingService.generate_assessment_csv(assessment)
        assert "CRAS - COMPLIANCE ASSESSMENT EXPORT" in csv_str
        assert "Report Test SME Ltd" in csv_str
        assert "PIN-REP-01" in csv_str

        # Generate Excel
        excel_stream = ReportingService.generate_excel_export(assessment)
        assert excel_stream is not None
        excel_bytes = excel_stream.getvalue()
        assert len(excel_bytes) > 1000

