import pytest
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, OrganizationUser
from app.models.assessment import ComplianceAssessment, AssessmentResponse
from app.models.regulatory import RegulatoryRequirement
from app.models.compliance_management import ComplianceGap
from datetime import date


def test_dashboard_partially_compliant_items_render(client, app):
    """Verifies that partially compliant items render correctly on the executive dashboard."""
    with app.app_context():
        # Setup organization and user
        org = Organization.query.filter_by(kra_pin="P099999999X").first()
        if not org:
            org = Organization(
                name="Partial Compliance Test Org Ltd",
                business_registration_number="PVT-PARTIAL-2026-01",
                kra_pin="P099999999X",
                industry_sector="Transport & Logistics",
                business_type="Private Limited Company",
                organization_size="Small (10-49)",
                county="Nairobi",
                employee_count=35,
                contact_email="test@partialorg.co.ke",
            )
            db.session.add(org)
            db.session.flush()

        user = User.query.filter_by(email="dash_test_user@cras.ke").first()
        if not user:
            user = User(
                email="dash_test_user@cras.ke",
                full_name="Dashboard Test User",
                is_active=True,
                is_verified=True,
            )
            user.set_password("TestPass2026!")
            db.session.add(user)
            db.session.flush()

        role = Role.query.filter_by(name=Role.COMPLIANCE_OFFICER).first()
        if role and not UserRole.query.filter_by(user_id=user.id, role_id=role.id).first():
            db.session.add(UserRole(user_id=user.id, role_id=role.id))

        if not OrganizationUser.query.filter_by(organization_id=org.id, user_id=user.id).first():
            db.session.add(OrganizationUser(organization_id=org.id, user_id=user.id, role_id=role.id if role else 1))

        # Create or verify assessment with partial compliance
        assessment = ComplianceAssessment.query.filter_by(organization_id=org.id).first()
        if not assessment:
            assessment = ComplianceAssessment(
                organization_id=org.id,
                created_by_id=user.id,
                title="2026 Q2 Test Review",
                assessment_period="2026 Q2",
                assessment_date=date(2026, 4, 15),
                status=ComplianceAssessment.STATUS_COMPLETED,
                overall_score=85.0,
                risk_classification="COMPLIANT",
                total_obligations=43,
                compliant_count=33,
                partially_compliant_count=10,
                non_compliant_count=0,
            )
            db.session.add(assessment)
            db.session.flush()

        # Add a partially compliant response if none exists
        existing_partial = AssessmentResponse.query.filter_by(
            assessment_id=assessment.id,
            response_value=AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
        ).first()

        if not existing_partial:
            req = RegulatoryRequirement.query.first()
            if req:
                resp = AssessmentResponse(
                    assessment_id=assessment.id,
                    requirement_id=req.id,
                    response_value=AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT,
                    response_score=0.5,
                    notes="Internal procedure drafted; awaiting executive sign-off.",
                )
                db.session.add(resp)
                gap = ComplianceGap(
                    organization_id=org.id,
                    assessment_id=assessment.id,
                    requirement_id=req.id,
                    domain_id=req.domain_id,
                    gap_title=f"Partial Gap for {req.code}",
                    gap_description="Pending finalization",
                    legal_reference=req.legal_reference,
                    severity=ComplianceGap.SEVERITY_MEDIUM,
                    status=ComplianceGap.STATUS_OPEN,
                )
                db.session.add(gap)

        db.session.commit()

        # Login
        login_resp = client.post("/auth/login", data={
            "email": "dash_test_user@cras.ke",
            "password": "TestPass2026!",
        }, follow_redirects=True)
        assert login_resp.status_code == 200

        # Set active organization in session
        with client.session_transaction() as sess:
            sess["active_organization_id"] = org.id

        # Access Dashboard
        resp = client.get("/dashboard/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # Verify Partially Compliant & Non-Compliant Metric Cards
        assert "Partially Compliant" in html
        assert "Remediation required" in html
        assert "Non-Compliant Items" in html
        assert "Critical compliance gaps" in html

        # Verify bottom icon boxes are removed from the metric cards
        assert "metric-icon-box" not in html

        # Verify Compliance Remediation Obligations section is removed from dashboard
        assert "Compliance Remediation Obligations" not in html
        assert "remediationTable" not in html
        assert "remediationSearchInput" not in html

        # Verify Direct Links: Both partially compliant and non-compliant point to assessment details
        assert f"/assessments/{assessment.id}" in html
        assert "/corrective-actions" in html
