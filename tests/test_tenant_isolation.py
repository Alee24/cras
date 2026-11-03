import pytest
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, OrganizationUser
from app.models.assessment import ComplianceAssessment
from datetime import date


def test_tenant_data_isolation(app, client):
    """Verifies that Organization A's records cannot be viewed by Organization B's users."""
    with app.app_context():
        # Setup Org A and User A
        org_a = Organization(
            name="Alpha Enterprises",
            business_registration_number="REG-ALPHA-01",
            kra_pin="PIN-ALPHA-01",
            contact_email="alpha@test.ke",
        )
        user_a = User(email="user_a@alpha.ke", full_name="User Alpha")
        user_a.set_password("AlphaPass123!")
        db.session.add_all([org_a, user_a])
        db.session.flush()

        role = Role.query.filter_by(name=Role.ORG_ADMIN).first()
        db.session.add(OrganizationUser(organization_id=org_a.id, user_id=user_a.id, role_id=role.id))

        # Setup Org B and User B
        org_b = Organization(
            name="Beta Logistics",
            business_registration_number="REG-BETA-02",
            kra_pin="PIN-BETA-02",
            contact_email="beta@test.ke",
        )
        user_b = User(email="user_b@beta.ke", full_name="User Beta")
        user_b.set_password("BetaPass123!")
        db.session.add_all([org_b, user_b])
        db.session.flush()

        db.session.add(OrganizationUser(organization_id=org_b.id, user_id=user_b.id, role_id=role.id))

        # Create assessment for Org A
        assessment_a = ComplianceAssessment(
            organization_id=org_a.id,
            created_by_id=user_a.id,
            title="Alpha Confidential Audit",
            assessment_period="2026 Q1",
            assessment_date=date.today(),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment_a)
        db.session.commit()
        assessment_a_id = assessment_a.id

    # Log in as User B
    client.post("/auth/login", data={"email": "user_b@beta.ke", "password": "BetaPass123!"})

    # User B attempts to access Org A's assessment
    resp = client.get(f"/assessments/{assessment_a_id}")
    # Must be 404 (or 403) due to organization-level tenant filter!
    assert resp.status_code in [404, 403]
