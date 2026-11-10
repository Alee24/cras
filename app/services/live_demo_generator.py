import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from app.models.base import db, utcnow
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, Department, OrganizationUser
from app.models.regulatory import RegulatoryDomain, RegulatoryRequirement
from app.models.scoring import ScoringPolicy, ScoringPolicyVersion
from app.models.assessment import ComplianceAssessment, AssessmentResponse, AssessmentDomainScore, AssessmentEvidence
from app.models.compliance_management import ComplianceGap, CorrectiveAction, ComplianceDeadline
from app.models.audit_and_notification import Notification, AuditLog
from app.services.scoring_service import ScoringEngine
from app.services.compliance_gap_service import ComplianceGapService
from app.services.seed_data import seed_roles_and_permissions, seed_scoring_policy, seed_regulatory_content, seed_statutory_calendar_rules


def ensure_sample_evidence_files(upload_dir_str: str) -> dict:
    """Creates realistic sample evidence files on disk for demonstration purposes."""
    upload_dir = Path(upload_dir_str)
    upload_dir.mkdir(parents=True, exist_ok=True)

    sample_files = {
        "KRA_Tax_Compliance_Certificate_2026.pdf": (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n"
            b"0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n",
            "application/pdf"
        ),
        "ODPC_Data_Controller_Registration_Cert.pdf": (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n"
            b"0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n",
            "application/pdf"
        ),
        "WIBA_Workplace_Injury_Insurance_Policy.pdf": (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n"
            b"0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n",
            "application/pdf"
        ),
        "OSHA_Workplace_Safety_Inspection_Report.pdf": (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n"
            b"0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n",
            "application/pdf"
        ),
        "eTIMS_System_Integration_Signoff.pdf": (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n"
            b"0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n",
            "application/pdf"
        ),
    }

    created_paths = {}
    for filename, (content, mime) in sample_files.items():
        stored_name = f"sample_demo_{filename}"
        target_path = upload_dir / stored_name
        if not target_path.exists():
            target_path.write_bytes(content)
        created_paths[filename] = {
            "stored_name": stored_name,
            "path": str(target_path),
            "size": len(content),
            "mime": mime,
        }

    return created_paths


def populate_comprehensive_live_data(upload_folder: str = "uploads") -> dict:
    """
    Populates full-fidelity, multi-period demonstration data across all regulatory domains:
    - 4 Kenyan SME companies with rich profiles and departments.
    - Multiple team members per company (Admin, Compliance Officer, Finance Manager, HR Manager).
    - Multi-quarter assessment progression (2025 Q3, 2025 Q4, 2026 Q1, 2026 Q2).
    - Diverse compliance gaps with realistic statutory references, consequences, and actions.
    - Active and historical corrective actions across all lifecycle states.
    - Statutory calendar deadlines (upcoming, overdue, completed).
    - Verified sample evidence records in the evidence vault.
    - In-app alerts and security audit logs.
    """
    seed_roles_and_permissions()
    policy, version = seed_scoring_policy()
    seed_regulatory_content()

    org_admin_role = Role.query.filter_by(name=Role.ORG_ADMIN).first()
    officer_role = Role.query.filter_by(name=Role.COMPLIANCE_OFFICER).first()
    finance_role = Role.query.filter_by(name=Role.FINANCE_MANAGER).first()
    hr_role = Role.query.filter_by(name=Role.HR_MANAGER).first()
    auditor_role = Role.query.filter_by(name=Role.AUDITOR).first()

    all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).order_by(RegulatoryRequirement.code).all()
    evidence_files = ensure_sample_evidence_files(upload_folder)

    # 4 Detailed Company Profiles
    companies_data = [
        # Company 1: Apex Logistics Solutions Ltd
        {
            "name": "Apex Logistics Solutions Ltd",
            "reg": "CPR/2020/88123",
            "pin": "P051992233M",
            "sector": "Transport & Logistics",
            "type": "Private Limited Company",
            "size": "Small (10-49)",
            "employees": 35,
            "county": "Nairobi",
            "email": "compliance@apexlogistics.co.ke",
            "address": "Apex Towers, 5th Floor, Mombasa Road, Nairobi",
            "website": "https://apexlogistics.co.ke",
            "phone": "+254 20 789 0100",
            "users": [
                ("Grace Mwangi", "grace@apexlogistics.co.ke", org_admin_role, "Executive Management", "+254 722 100 200"),
                ("Kevin Ochieng", "kevin.compliance@apexlogistics.co.ke", officer_role, "Legal & Compliance", "+254 733 200 300"),
                ("Peter Kamau", "peter.finance@apexlogistics.co.ke", finance_role, "Finance & Accounts", "+254 711 300 400"),
                ("Mercy Chebet", "mercy.hr@apexlogistics.co.ke", hr_role, "Human Resources", "+254 700 400 500"),
            ],
            # Quarter progression: 2025 Q3 -> 2025 Q4 -> 2026 Q1 -> 2026 Q2
            "quarters": [
                ("2025 Q3 Statutory Audit", "2025 Q3", date(2025, 9, 30), 0.82),
                ("2025 Q4 Statutory Audit", "2025 Q4", date(2025, 12, 31), 0.88),
                ("2026 Q1 Statutory Compliance Assessment", "2026 Q1", date(2026, 3, 31), 1.00),
                ("2026 Q2 Interim Review", "2026 Q2", date(2026, 6, 30), 0.95),
            ],
            "evidence_keys": ["KRA_Tax_Compliance_Certificate_2026.pdf", "ODPC_Data_Controller_Registration_Cert.pdf", "WIBA_Workplace_Injury_Insurance_Policy.pdf"],
        },

        # Company 2: Kilimani Digital Health Clinic
        {
            "name": "Kilimani Digital Health Clinic",
            "reg": "CPR/2022/44112",
            "pin": "P052441122H",
            "sector": "Healthcare & Pharmaceuticals",
            "type": "Private Limited Company",
            "size": "Small (10-49)",
            "employees": 24,
            "county": "Nairobi",
            "email": "admin@kilimanihealth.co.ke",
            "address": "Argwings Kodhek Road, Kilimani, Nairobi",
            "website": "https://kilimanihealth.co.ke",
            "phone": "+254 20 456 7890",
            "users": [
                ("Dr. Brian Otieno", "dr.otieno@kilimanihealth.co.ke", org_admin_role, "Clinical Administration", "+254 712 900 111"),
                ("Faith Wanjiru", "faith.compliance@kilimanihealth.co.ke", officer_role, "Quality & Compliance", "+254 722 800 222"),
                ("Daniel Mutua", "daniel.finance@kilimanihealth.co.ke", finance_role, "Finance & Billing", "+254 733 700 333"),
                ("Sarah Jepchirchir", "sarah.hr@kilimanihealth.co.ke", hr_role, "Staff & Welfare", "+254 744 600 444"),
            ],
            "quarters": [
                ("2025 Q3 Baseline Healthcare Review", "2025 Q3", date(2025, 9, 30), 0.48),
                ("2025 Q4 Health Compliance Audit", "2025 Q4", date(2025, 12, 31), 0.55),
                ("2026 Q1 Healthcare Compliance Assessment", "2026 Q1", date(2026, 3, 31), 0.64),
                ("2026 Q2 Follow-up Audit", "2026 Q2", date(2026, 6, 30), 0.72),
            ],
            "evidence_keys": ["ODPC_Data_Controller_Registration_Cert.pdf", "OSHA_Workplace_Safety_Inspection_Report.pdf"],
        },

        # Company 3: Rift Valley Fresh Produce Ltd
        {
            "name": "Rift Valley Fresh Produce Ltd",
            "reg": "CPR/2019/33221",
            "pin": "P051332211A",
            "sector": "Agriculture & Agribusiness",
            "type": "Private Limited Company",
            "size": "Medium (50-249)",
            "employees": 65,
            "county": "Nakuru",
            "email": "info@riftvalleyproduce.co.ke",
            "address": "Industrial Area, Off George Morara Road, Nakuru",
            "website": "https://riftvalleyproduce.co.ke",
            "phone": "+254 51 221 4455",
            "users": [
                ("Kiprono Koech", "koech@riftvalleyproduce.co.ke", org_admin_role, "Operations & General Management", "+254 721 112 233"),
                ("Agnes Cherono", "agnes.compliance@riftvalleyproduce.co.ke", officer_role, "Standards & Safety", "+254 732 223 344"),
                ("Samuel Ndegwa", "samuel.finance@riftvalleyproduce.co.ke", finance_role, "Finance & Procurement", "+254 713 334 455"),
            ],
            "quarters": [
                ("2025 Q3 Farm Audit", "2025 Q3", date(2025, 9, 30), 0.18),
                ("2025 Q4 Packhouse Compliance Audit", "2025 Q4", date(2025, 12, 31), 0.28),
                ("2026 Initial Compliance Baseline", "Initial Baseline 2026", date(2026, 3, 31), 0.35),
                ("2026 Q2 Remediation Check", "2026 Q2", date(2026, 6, 30), 0.45),
            ],
            "evidence_keys": ["eTIMS_System_Integration_Signoff.pdf"],
        },

        # Company 4: Savanna Retail Distributors Ltd
        {
            "name": "Savanna Retail Distributors Ltd",
            "reg": "CPR/2023/11099",
            "pin": "P053110992R",
            "sector": "Retail & Wholesale",
            "type": "Private Limited Company",
            "size": "Small (10-49)",
            "employees": 18,
            "county": "Mombasa",
            "email": "admin@savannaretail.co.ke",
            "address": "Nyali Commercial Complex, Links Road, Mombasa",
            "website": "https://savannaretail.co.ke",
            "phone": "+254 41 447 8899",
            "users": [
                ("Hassan Ali", "hassan@savannaretail.co.ke", org_admin_role, "Executive Management", "+254 720 556 677"),
                ("Amina Mwinyi", "amina.compliance@savannaretail.co.ke", officer_role, "Compliance & Audit", "+254 735 667 788"),
                ("Omar Salim", "omar.finance@savannaretail.co.ke", finance_role, "Accounts & Tax", "+254 715 778 899"),
            ],
            "quarters": [
                ("2025 Q3 Inception Review", "2025 Q3", date(2025, 9, 30), 0.45),
                ("2025 Q4 Wholesale Audit", "2025 Q4", date(2025, 12, 31), 0.50),
                ("2026 Q1 Wholesale Compliance Audit", "2026 Q1", date(2026, 3, 31), 0.68),
                ("2026 Q2 Expansion Review", "2026 Q2", date(2026, 6, 30), 0.78),
            ],
            "evidence_keys": ["KRA_Tax_Compliance_Certificate_2026.pdf", "eTIMS_System_Integration_Signoff.pdf"],
        },
    ]

    total_assessments_created = 0
    total_gaps_created = 0
    total_actions_created = 0
    total_evidence_created = 0

    for c_idx, c_data in enumerate(companies_data):
        org = Organization.query.filter_by(kra_pin=c_data["pin"]).first()
        if not org:
            org = Organization(
                name=c_data["name"],
                business_registration_number=c_data["reg"],
                kra_pin=c_data["pin"],
                industry_sector=c_data["sector"],
                business_type=c_data["type"],
                organization_size=c_data["size"],
                employee_count=c_data["employees"],
                county=c_data["county"],
                contact_email=c_data["email"],
                physical_address=c_data["address"],
                website=c_data["website"],
                phone_number=c_data["phone"],
                registration_date=date(2021, 6, 1),
                is_active=True,
            )
            db.session.add(org)
            db.session.flush()

        # Seed Kenya statutory calendar rules for this company
        seed_statutory_calendar_rules(org.id)

        # Departments
        depts_map = {}
        for d_name in ["Executive Management", "Legal & Compliance", "Finance & Accounts", "Human Resources", "Operations"]:
            d_code = d_name.split()[0][:4].upper()
            dept = Department.query.filter_by(organization_id=org.id, name=d_name).first()
            if not dept:
                dept = Department(organization_id=org.id, name=d_name, code=d_code, description=f"{d_name} functional unit")
                db.session.add(dept)
                db.session.flush()
            depts_map[d_name] = dept

        # Users
        company_users = []
        for u_name, u_email, u_role, u_dept, u_phone in c_data["users"]:
            user = User.query.filter_by(email=u_email).first()
            if not user:
                user = User(
                    email=u_email,
                    full_name=u_name,
                    phone_number=u_phone,
                    is_active=True,
                    is_verified=True,
                )
                user.set_password("CRAS@SME2026!")
                db.session.add(user)
                db.session.flush()

            if u_role and not UserRole.query.filter_by(user_id=user.id, role_id=u_role.id).first():
                db.session.add(UserRole(user_id=user.id, role_id=u_role.id))

            # Org membership
            dept_obj = depts_map.get(u_dept, list(depts_map.values())[0])
            membership = OrganizationUser.query.filter_by(organization_id=org.id, user_id=user.id).first()
            if not membership:
                membership = OrganizationUser(
                    organization_id=org.id,
                    user_id=user.id,
                    role_id=u_role.id,
                    department_id=dept_obj.id,
                    is_primary=(u_role == org_admin_role),
                )
                db.session.add(membership)

            company_users.append(user)

        lead_user = company_users[0]
        compliance_user = company_users[1] if len(company_users) > 1 else lead_user
        finance_user = company_users[2] if len(company_users) > 2 else lead_user
        hr_user = company_users[3] if len(company_users) > 3 else lead_user

        # Seed statutory deadlines with rich dates
        seed_statutory_calendar_rules(org.id)

        # Update some deadlines to overdue or completed for live realism
        deadlines = ComplianceDeadline.query.filter_by(organization_id=org.id).all()
        for d_idx, dl in enumerate(deadlines):
            if d_idx == 0: # Monthly PAYE - Overdue for high-risk / moderate companies
                if c_idx in [1, 2]:
                    dl.current_due_date = date.today() - timedelta(days=4)
                    dl.status = ComplianceDeadline.STATUS_OVERDUE
                else:
                    dl.status = ComplianceDeadline.STATUS_COMPLETED
                    dl.completed_at = utcnow() - timedelta(days=2)
            elif d_idx == 1: # NSSF - Upcoming in 5 days
                dl.current_due_date = date.today() + timedelta(days=5)
                dl.status = ComplianceDeadline.STATUS_PENDING
            elif d_idx == 2: # SHIF - Upcoming in 5 days
                dl.current_due_date = date.today() + timedelta(days=5)
                dl.status = ComplianceDeadline.STATUS_PENDING
            elif d_idx == 3: # VAT - Upcoming on 20th
                dl.current_due_date = date.today() + timedelta(days=16)
                dl.status = ComplianceDeadline.STATUS_PENDING

        # Multi-period Assessments (Multi-Quarter progression)
        for a_title, a_period, a_date, target_score_ratio in c_data["quarters"]:
            assessment = ComplianceAssessment.query.filter_by(organization_id=org.id, assessment_period=a_period).first()
            if not assessment:
                assessment = ComplianceAssessment(
                    organization_id=org.id,
                    created_by_id=compliance_user.id,
                    scoring_policy_version_id=version.id,
                    title=a_title,
                    assessment_period=a_period,
                    assessment_date=a_date,
                    status=ComplianceAssessment.STATUS_COMPLETED,
                    notes=f"Quarterly statutory compliance review for {a_period}.",
                )
                db.session.add(assessment)
                db.session.flush()
                total_assessments_created += 1

                # Generate responses to closely reflect target_score_ratio
                # If target is 1.0 -> all compliant
                # If target is 0.65 -> ~65% compliant, ~15% partial, ~20% non-compliant
                # If target is 0.25 -> ~15% compliant, ~20% partial, ~65% non-compliant
                for r_idx, req in enumerate(all_reqs):
                    # Deterministic hash for variety across requirements
                    seed_val = (r_idx * 17 + int(target_score_ratio * 100)) % 100
                    threshold_comp = int(target_score_ratio * 85)
                    threshold_part = threshold_comp + 20

                    if seed_val < threshold_comp:
                        resp_val = AssessmentResponse.RESPONSE_COMPLIANT
                        notes = "Verified against registered documentation."
                    elif seed_val < threshold_part:
                        resp_val = AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
                        notes = "Partially implemented; workflow revision ongoing."
                    else:
                        resp_val = AssessmentResponse.RESPONSE_NON_COMPLIANT
                        notes = "Gap identified; remediation required."

                    resp = AssessmentResponse(
                        assessment_id=assessment.id,
                        requirement_id=req.id,
                        response_value=resp_val,
                        notes=notes,
                        updated_by_id=compliance_user.id,
                    )
                    db.session.add(resp)

                db.session.flush()
                ScoringEngine.apply_and_persist_scores(assessment, version)
                gaps_cnt = ComplianceGapService.sync_gaps_for_assessment(assessment)
                total_gaps_created += gaps_cnt

        # Attach sample evidence to latest assessment
        latest_assessment = ComplianceAssessment.query.filter_by(organization_id=org.id).order_by(
            ComplianceAssessment.assessment_date.desc()
        ).first()

        if latest_assessment:
            for ev_key in c_data.get("evidence_keys", []):
                ev_info = evidence_files.get(ev_key)
                if ev_info:
                    # Pick an appropriate requirement
                    match_req = all_reqs[0]
                    if "Tax" in ev_key:
                        match_req = next((r for r in all_reqs if r.code == "TAX-002"), all_reqs[0])
                    elif "ODPC" in ev_key:
                        match_req = next((r for r in all_reqs if r.code == "DP-001"), all_reqs[0])
                    elif "WIBA" in ev_key:
                        match_req = next((r for r in all_reqs if r.code == "EMP-012"), all_reqs[0])
                    elif "OSHA" in ev_key:
                        match_req = next((r for r in all_reqs if r.code == "EMP-011"), all_reqs[0])
                    elif "eTIMS" in ev_key:
                        match_req = next((r for r in all_reqs if r.code == "TAX-007"), all_reqs[0])

                    existing_ev = AssessmentEvidence.query.filter_by(
                        organization_id=org.id,
                        assessment_id=latest_assessment.id,
                        requirement_id=match_req.id,
                    ).first()

                    if not existing_ev:
                        unique_stored_name = f"org{org.id}_demo_{uuid.uuid4().hex[:8]}_{ev_key}"
                        unique_dest_path = Path(upload_folder) / unique_stored_name
                        if not unique_dest_path.exists():
                            unique_dest_path.write_bytes(Path(ev_info["path"]).read_bytes())

                        ev = AssessmentEvidence(
                            organization_id=org.id,
                            assessment_id=latest_assessment.id,
                            requirement_id=match_req.id,
                            uploaded_by_id=compliance_user.id,
                            original_filename=ev_key,
                            stored_filename=unique_stored_name,
                            file_size=ev_info["size"],
                            mime_type=ev_info["mime"],
                            file_path=str(unique_dest_path),
                            description=f"Official verified document for {match_req.code}",
                            verification_status=AssessmentEvidence.STATUS_VERIFIED,
                            uploaded_at=utcnow() - timedelta(days=5),
                        )
                        db.session.add(ev)
                        total_evidence_created += 1

        # Generate realistic corrective action tasks for open compliance gaps
        open_gaps = ComplianceGap.query.filter_by(
            organization_id=org.id, status=ComplianceGap.STATUS_OPEN
        ).limit(6).all()

        action_statuses = [
            CorrectiveAction.STATUS_IN_PROGRESS,
            CorrectiveAction.STATUS_ASSIGNED,
            CorrectiveAction.STATUS_PENDING_VERIFICATION,
            CorrectiveAction.STATUS_RESOLVED,
            CorrectiveAction.STATUS_OPEN,
            CorrectiveAction.STATUS_CLOSED,
        ]

        for idx, gap in enumerate(open_gaps):
            existing_act = CorrectiveAction.query.filter_by(organization_id=org.id, gap_id=gap.id).first()
            if not existing_act:
                # Assign to appropriate manager
                assigned = compliance_user
                if gap.domain and gap.domain.code == "TAX":
                    assigned = finance_user
                elif gap.domain and gap.domain.code == "LABOUR":
                    assigned = hr_user

                status = action_statuses[idx % len(action_statuses)]
                due = date.today() + timedelta(days=(7 * (idx + 1) - 10))

                action = CorrectiveAction(
                    organization_id=org.id,
                    gap_id=gap.id,
                    assessment_id=gap.assessment_id,
                    requirement_id=gap.requirement_id,
                    title=f"Remediate {gap.gap_title[:60]}",
                    action_description=gap.recommended_action or "Review statutory obligations and implement operational safeguards.",
                    priority=CorrectiveAction.PRIORITY_HIGH if gap.severity in ["CRITICAL", "HIGH"] else CorrectiveAction.PRIORITY_MEDIUM,
                    status=status,
                    assigned_to_id=assigned.id,
                    created_by_id=lead_user.id,
                    due_date=due,
                    resolution_notes="Remediation steps completed and verified by internal audit team." if status in [CorrectiveAction.STATUS_RESOLVED, CorrectiveAction.STATUS_CLOSED] else None,
                    completed_at=utcnow() - timedelta(days=2) if status in [CorrectiveAction.STATUS_RESOLVED, CorrectiveAction.STATUS_CLOSED] else None,
                )
                db.session.add(action)

                if status in [CorrectiveAction.STATUS_RESOLVED, CorrectiveAction.STATUS_CLOSED]:
                    gap.status = ComplianceGap.STATUS_RESOLVED
                    gap.resolved_at = utcnow() - timedelta(days=2)
                elif status == CorrectiveAction.STATUS_ASSIGNED:
                    gap.status = ComplianceGap.STATUS_ASSIGNED
                elif status == CorrectiveAction.STATUS_IN_PROGRESS:
                    gap.status = ComplianceGap.STATUS_IN_PROGRESS

                total_actions_created += 1

        # Create notifications for active users
        for u in [lead_user, compliance_user, finance_user]:
            Notification.query.filter_by(user_id=u.id).delete()
            notifs = [
                Notification(
                    user_id=u.id,
                    organization_id=org.id,
                    title="Upcoming Statutory Deadline: PAYE Remittance",
                    message="Monthly employee PAYE returns and remittances are due by the 9th on KRA iTax.",
                    notification_type="DEADLINE",
                    link_url="/calendar/",
                    is_read=False,
                    created_at=utcnow() - timedelta(hours=3),
                ),
                Notification(
                    user_id=u.id,
                    organization_id=org.id,
                    title="Assessment Finalized: 2026 Q1",
                    message="The quarterly statutory compliance assessment has been finalized with live scores calculated.",
                    notification_type="ASSESSMENT",
                    link_url="/assessments/",
                    is_read=False,
                    created_at=utcnow() - timedelta(hours=12),
                ),
                Notification(
                    user_id=u.id,
                    organization_id=org.id,
                    title="New Corrective Action Task Assigned",
                    message="You have open remediation actions requiring departmental attention.",
                    notification_type="ACTION",
                    link_url="/corrective-actions/",
                    is_read=True,
                    created_at=utcnow() - timedelta(days=2),
                ),
            ]
            db.session.add_all(notifs)

        # Audit logs
        AuditLog.query.filter_by(organization_id=org.id).delete()
        audit_events = [
            ("LOGIN_SUCCESS", "User", lead_user.id, {"email": lead_user.email}, lead_user.id, org.id),
            ("SUBMIT_ASSESSMENT", "ComplianceAssessment", latest_assessment.id if latest_assessment else 1, {"period": "2026 Q1"}, compliance_user.id, org.id),
            ("CREATE_CORRECTIVE_ACTION", "CorrectiveAction", 1, {"priority": "HIGH"}, lead_user.id, org.id),
            ("EXPORT_PDF_REPORT", "ComplianceAssessment", latest_assessment.id if latest_assessment else 1, {"format": "PDF"}, finance_user.id, org.id),
        ]
        for act, ent, ent_id, dtls, uid, oid in audit_events:
            db.session.add(AuditLog(
                user_id=uid,
                organization_id=oid,
                action=act,
                entity_type=ent,
                entity_id=str(ent_id),
                details=str(dtls),
                ip_address="127.0.0.1",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                created_at=utcnow() - timedelta(hours=4),
            ))

    db.session.commit()

    total_orgs = Organization.query.count()
    total_assessments = ComplianceAssessment.query.count()
    total_gaps = ComplianceGap.query.count()
    total_actions = CorrectiveAction.query.count()
    total_events = ComplianceDeadline.query.count()
    total_evidence = AssessmentEvidence.query.count()

    return {
        "status": "success",
        "organizations": total_orgs,
        "assessments": total_assessments,
        "gaps": total_gaps,
        "actions": total_actions,
        "calendar_events": total_events,
        "evidence_files": total_evidence,
        "companies_seeded": total_orgs,
        "assessments_created": total_assessments,
        "gaps_created": total_gaps,
        "actions_created": total_actions,
        "evidence_created": total_evidence,
    }
