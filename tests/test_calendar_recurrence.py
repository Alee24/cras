import pytest
from datetime import date
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization
from app.models.compliance_management import ComplianceDeadline
from app.models.regulatory import RegulatoryDomain, RegulatoryCategory, RegulatoryRequirement, ComplianceQuestion
from app.services.seed_data import calculate_initial_statutory_due_date, seed_statutory_calendar_rules


def get_or_create_test_org():
    org = Organization.query.first()
    if not org:
        org = Organization(
            name="Test Org",
            business_registration_number="CPR/2026/01",
            kra_pin="P051234567Z",
            contact_email="test@testorg.co.ke",
            industry_sector="Logistics",
        )
        db.session.add(org)
        db.session.commit()
    return org


def get_or_create_super_admin():
    admin = User.query.filter_by(email="admin@cras.ke").first()
    if not admin:
        admin = User(email="admin@cras.ke", full_name="Super Admin")
        admin.set_password("Admin@CRAS2026!")
        db.session.add(admin)
        db.session.flush()
        super_role = Role.query.filter_by(name=Role.SUPER_ADMIN).first()
        if not super_role:
            super_role = Role(name=Role.SUPER_ADMIN, display_name="Super Administrator")
            db.session.add(super_role)
            db.session.flush()
        db.session.add(UserRole(user_id=admin.id, role_id=super_role.id))
        db.session.commit()
    return admin


def test_calculate_initial_statutory_due_date_november_registration():
    """Verify that when a company registers in November, statutory deadlines dynamically

    calculate next occurrences and never pick hardcoded April.
    """
    reg_date = date(2026, 11, 16)

    # Monthly 9th (PAYE, NSSF, SHIF) - 9th has passed for Nov, so next is Dec 9
    paye_due = calculate_initial_statutory_due_date("MONTHLY", day_of_month=9, base_date=reg_date)
    assert paye_due == date(2026, 12, 9)
    assert paye_due.month != 4, "Must never pick April for November registration"

    # Monthly 20th (VAT) - 20th is upcoming this month, so Nov 20
    vat_due = calculate_initial_statutory_due_date("MONTHLY", day_of_month=20, base_date=reg_date)
    assert vat_due == date(2026, 11, 20)

    # Annual (Corporate Tax, June 30) - June 30, 2026 has passed, next is June 30, 2027
    cit_due = calculate_initial_statutory_due_date("ANNUAL", annual_month=6, annual_day=30, base_date=reg_date)
    assert cit_due == date(2027, 6, 30)


def test_annual_statutory_deadline_advancement_and_cycle_completion(app):
    """Annual deadline (30th June 2026) once marked complete moves to 30th June 2027

    while status remains COMPLETED through the end of 2026.
    """
    with app.app_context():
        org = get_or_create_test_org()
        dl = ComplianceDeadline(
            organization_id=org.id,
            title="Annual Corporate Income Tax Return (Dec Year-End)",
            statutory_rule="30th June annually",
            recurrence=ComplianceDeadline.RECURRENCE_ANNUAL,
            current_due_date=date(2026, 6, 30),
            status=ComplianceDeadline.STATUS_PENDING,
            is_active=True,
        )
        db.session.add(dl)
        db.session.commit()

        # Advance upon completion
        dl.advance_to_next_cycle(today=date(2026, 6, 15))
        db.session.commit()

        assert dl.current_due_date == date(2027, 6, 30), "Current due date must advance to next year"
        assert dl.last_completed_due_date == date(2026, 6, 30)
        assert dl.status == ComplianceDeadline.STATUS_COMPLETED
        assert dl.completed_cycle_until == date(2026, 12, 31), "Status must remain completed through Dec 31, 2026"

        # During 2026 (e.g. November 17, 2026), status remains COMPLETED
        dl.refresh_status_for_date(today=date(2026, 11, 17))
        assert dl.status == ComplianceDeadline.STATUS_COMPLETED

        # On Jan 1, 2027, cycle has concluded so status resets to PENDING for the 2027 deadline
        dl.refresh_status_for_date(today=date(2027, 1, 1))
        assert dl.status == ComplianceDeadline.STATUS_PENDING
        assert dl.completed_cycle_until is None

        # Reopening restores previous due date
        dl.reopen_previous_cycle(today=date(2026, 11, 17))
        db.session.commit()
        assert dl.current_due_date == date(2026, 6, 30)
        assert dl.status == ComplianceDeadline.STATUS_OVERDUE  # 2026-06-30 is past 2026-11-17


def test_monthly_statutory_deadline_advancement_and_reopen(app):
    """Monthly deadline (9th of month) once marked complete moves to next month's 9th

    while status remains COMPLETED until the end of the completed month.
    """
    with app.app_context():
        org = get_or_create_test_org()
        dl = ComplianceDeadline(
            organization_id=org.id,
            title="Monthly PAYE Return & Remittance",
            statutory_rule="9th of every month",
            recurrence=ComplianceDeadline.RECURRENCE_MONTHLY,
            current_due_date=date(2026, 11, 9),
            status=ComplianceDeadline.STATUS_OVERDUE,
            is_active=True,
        )
        db.session.add(dl)
        db.session.commit()

        # Mark complete on Nov 17
        dl.advance_to_next_cycle(today=date(2026, 11, 17))
        db.session.commit()

        assert dl.current_due_date == date(2026, 12, 9), "Must advance to December 9"
        assert dl.last_completed_due_date == date(2026, 11, 9)
        assert dl.status == ComplianceDeadline.STATUS_COMPLETED
        assert dl.completed_cycle_until == date(2026, 11, 30)

        # Within November, status remains COMPLETED
        dl.refresh_status_for_date(today=date(2026, 11, 25))
        assert dl.status == ComplianceDeadline.STATUS_COMPLETED

        # On Dec 1, cycle expires and status becomes PENDING for Dec 9 deadline
        dl.refresh_status_for_date(today=date(2026, 12, 1))
        assert dl.status == ComplianceDeadline.STATUS_PENDING

        # Reopen restores November 9
        dl.reopen_previous_cycle(today=date(2026, 11, 17))
        assert dl.current_due_date == date(2026, 11, 9)
        assert dl.status == ComplianceDeadline.STATUS_OVERDUE


def test_super_admin_regulatory_content_crud(client, app):
    """Verifies that Super Admin can create, edit, toggle, and manage regulatory requirements."""
    with app.app_context():
        admin = get_or_create_super_admin()
        domain = RegulatoryDomain.query.first()
        category = RegulatoryCategory.query.filter_by(domain_id=domain.id).first()
        admin_id = admin.id
        domain_id = domain.id
        category_id = category.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True

    # 1. Create a new requirement via POST
    new_data = {
        "code": "TEST-REG-99",
        "title": "Automated Testing Statutory Requirement",
        "domain_id": domain_id,
        "category_id": category_id,
        "plain_description": "Requirement created via automated test suite.",
        "legal_reference": "Test Compliance Act 2026, Section 1",
        "applicability_rule": "All SMEs",
        "required_evidence_desc": "Test Report",
        "risk_weight": "2.5",
        "potential_consequence": "Test Fine",
        "recommended_corrective_action": "Run pytest suite",
        "verification_status": "VERIFIED",
        "question_text": "Is this automated test requirement compliant?",
        "question_help": "Verify via test client",
    }
    resp = client.post("/admin/regulatory-content/new", data=new_data, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        created_req = RegulatoryRequirement.query.filter_by(code="TEST-REG-99").first()
        assert created_req is not None
        assert created_req.risk_weight == 2.5
        assert len(created_req.questions) == 1
        assert "compliant?" in created_req.questions[0].question_text
        req_id = created_req.id

    # 2. Edit requirement via POST
    edit_data = {
        "code": "TEST-REG-99-EDITED",
        "title": "Automated Testing Requirement (Updated)",
        "domain_id": domain_id,
        "category_id": category_id,
        "plain_description": "Updated description.",
        "legal_reference": "Test Compliance Act 2026, Section 2",
        "applicability_rule": "All SMEs",
        "required_evidence_desc": "Updated Evidence",
        "risk_weight": "3.0",
        "potential_consequence": "Max Fine",
        "recommended_corrective_action": "Fix test",
        "verification_status": "REQUIRES_LEGAL_REVIEW",
        "is_active": "1",
        "question_text": "Updated question text?",
        "question_help": "Updated help",
    }
    resp_edit = client.post(f"/admin/regulatory-content/{req_id}/edit", data=edit_data, follow_redirects=True)
    assert resp_edit.status_code == 200

    with app.app_context():
        updated_req = RegulatoryRequirement.query.get(req_id)
        assert updated_req.code == "TEST-REG-99-EDITED"
        assert updated_req.risk_weight == 3.0
        assert updated_req.verification_status == "REQUIRES_LEGAL_REVIEW"

    # 3. Toggle requirement active/inactive
    resp_toggle = client.post(f"/admin/regulatory-content/{req_id}/toggle", follow_redirects=True)
    assert resp_toggle.status_code == 200
    with app.app_context():
        toggled_req = RegulatoryRequirement.query.get(req_id)
        assert toggled_req.is_active is False

    # 4. Delete requirement
    resp_del = client.post(f"/admin/regulatory-content/{req_id}/delete", follow_redirects=True)
    assert resp_del.status_code == 200
    with app.app_context():
        deleted_req = RegulatoryRequirement.query.get(req_id)
        assert deleted_req is None
