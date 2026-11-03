import pytest
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, OrganizationUser
from app.models.base import db


def test_password_hashing(app):
    with app.app_context():
        user = User(email="test_hash@cras.ke", full_name="Hash Test User")
        user.set_password("SecureSecretPass123!")
        
        assert user.password_hash != "SecureSecretPass123!"
        assert user.check_password("SecureSecretPass123!") is True
        assert user.check_password("WrongPassword") is False


def test_user_lockout_after_max_failed_attempts(app):
    with app.app_context():
        user = User(email="lockout_user@cras.ke", full_name="Lockout Test User")
        user.set_password("CorrectPassword123!")
        db.session.add(user)
        db.session.commit()

        assert user.is_locked is False

        # Fail 5 times
        for _ in range(5):
            user.record_failed_login(max_attempts=5, lock_minutes=15)
        db.session.commit()

        assert user.failed_login_attempts == 5
        assert user.is_locked is True

        # Successful login resets
        user.record_successful_login()
        db.session.commit()
        assert user.failed_login_attempts == 0
        assert user.is_locked is False


def test_role_based_permissions(app):
    with app.app_context():
        super_role = Role.query.filter_by(name=Role.SUPER_ADMIN).first()
        org_admin_role = Role.query.filter_by(name=Role.ORG_ADMIN).first()

        super_user = User(email="super_test@cras.ke", full_name="Super Admin User")
        super_user.set_password("Pass1234!")
        db.session.add(super_user)
        db.session.flush()
        db.session.add(UserRole(user_id=super_user.id, role_id=super_role.id))

        standard_user = User(email="standard_test@cras.ke", full_name="Standard Org User")
        standard_user.set_password("Pass1234!")
        db.session.add(standard_user)
        db.session.flush()
        db.session.add(UserRole(user_id=standard_user.id, role_id=org_admin_role.id))

        db.session.commit()

        assert super_user.is_super_admin is True
        assert super_user.has_role(Role.ORG_ADMIN) is True # Super admin has all roles
        assert standard_user.is_super_admin is False
        assert standard_user.has_role(Role.ORG_ADMIN) is True
        assert standard_user.has_role(Role.COMPLIANCE_OFFICER) is False


def test_sme_registration_workflow(client, app):
    with app.app_context():
        response = client.post("/auth/register", data={
            "full_name": "Samuel Mutua",
            "email": "samuel@muthuaindustries.co.ke",
            "phone_number": "+254711223344",
            "organization_name": "Mutua Agro Industries Ltd",
            "business_registration_number": "PVT-998877",
            "kra_pin": "P099887766A",
            "industry_sector": "Agriculture & Agribusiness",
            "business_type": "Private Limited Company",
            "organization_size": "Small (10-49)",
            "employee_count": 28,
            "county": "Kiambu",
            "password": "Password2026!",
            "confirm_password": "Password2026!",
            "terms_agreed": "y",
        }, follow_redirects=True)

        assert response.status_code == 200

        # Verify DB records created
        user = User.query.filter_by(email="samuel@muthuaindustries.co.ke").first()
        assert user is not None
        assert user.full_name == "Samuel Mutua"

        org = Organization.query.filter_by(kra_pin="P099887766A").first()
        assert org is not None
        assert org.name == "Mutua Agro Industries Ltd"
        assert org.county == "Kiambu"

        # Check membership and role
        membership = OrganizationUser.query.filter_by(user_id=user.id, organization_id=org.id).first()
        assert membership is not None
        assert membership.role.name == Role.ORG_ADMIN
