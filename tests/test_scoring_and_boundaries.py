import pytest
from app.models.base import db
from app.models.scoring import ScoringPolicyVersion
from app.services.scoring_service import ScoringEngine, ScoringValidationError
from app.models.assessment import ComplianceAssessment, AssessmentResponse
from app.models.organization import Organization
from app.models.auth import User
from app.models.regulatory import RegulatoryRequirement, RegulatoryDomain
from datetime import date


def test_rag_threshold_boundaries(app):
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        assert version is not None

        # Test threshold boundary points specified in proposal:
        # 0 - 49.99: High Risk (Red)
        # 50 - 79.99: Moderate Risk (Amber)
        # 80 - 100: Compliant (Green)

        assert version.classify_score(0.0) == "HIGH_RISK"
        assert version.classify_score(49.98) == "HIGH_RISK"
        assert version.classify_score(49.99) == "HIGH_RISK"
        
        assert version.classify_score(50.00) == "MODERATE_RISK"
        assert version.classify_score(65.50) == "MODERATE_RISK"
        assert version.classify_score(79.99) == "MODERATE_RISK"
        
        assert version.classify_score(80.00) == "COMPLIANT"
        assert version.classify_score(95.00) == "COMPLIANT"
        assert version.classify_score(100.00) == "COMPLIANT"


def test_unassessed_obligations_fail_submission(app):
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization(
            name="Incomplete Test Org",
            business_registration_number="REG-INC-001",
            kra_pin="PIN-INC-001",
            contact_email="inc@test.ke",
        )
        user = User(email="assessor_inc@test.ke", full_name="Incomplete Assessor")
        user.set_password("Pass123!")
        db.session.add_all([org, user])
        db.session.flush()

        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=user.id,
            scoring_policy_version_id=version.id,
            title="Incomplete Assessment Test",
            assessment_period="2026 Q1",
            assessment_date=date.today(),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment)
        db.session.flush()

        # Add only 1 response, leaving all other requirements unassessed
        first_req = RegulatoryRequirement.query.first()
        resp = AssessmentResponse(
            assessment_id=assessment.id,
            requirement_id=first_req.id,
            response_value=AssessmentResponse.RESPONSE_COMPLIANT,
        )
        db.session.add(resp)
        db.session.commit()

        # Scoring engine MUST throw ScoringValidationError
        with pytest.raises(ScoringValidationError) as exc_info:
            ScoringEngine.calculate_assessment_scores(assessment, version)

        assert "unassessed obligation" in str(exc_info.value).lower()
