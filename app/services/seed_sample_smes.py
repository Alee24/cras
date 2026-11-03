from datetime import date
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, Department, OrganizationUser
from app.models.regulatory import RegulatoryRequirement
from app.models.scoring import ScoringPolicyVersion
from app.models.assessment import ComplianceAssessment, AssessmentResponse
from app.services.scoring_service import ScoringEngine
from app.services.compliance_gap_service import ComplianceGapService
from app.services.seed_data import seed_statutory_calendar_rules


def seed_synthetic_smes():
    """Seeds the 4 complete synthetic SME organizations and completed assessments for demonstration and evaluation."""
    version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
    org_admin_role = Role.query.filter_by(name=Role.ORG_ADMIN).first()
    officer_role = Role.query.filter_by(name=Role.COMPLIANCE_OFFICER).first()
    all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).all()

    smes = [
        # SME 1: Compliant (Apex Logistics)
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
            "user_name": "Grace Mwangi",
            "user_email": "grace@apexlogistics.co.ke",
            "title": "2026 Q1 Statutory Compliance Assessment",
            "period": "2026 Q1",
            "date": date(2026, 3, 31),
            "response_func": lambda req: AssessmentResponse.RESPONSE_COMPLIANT,
        },
        # SME 2: Moderate Risk (Kilimani Digital Health)
        {
            "name": "Kilimani Digital Health Clinic",
            "reg": "CPR/2022/44112",
            "pin": "P052441122H",
            "sector": "Healthcare & Pharmaceuticals",
            "type": "Private Limited Company",
            "size": "Small (10-49)",
            "employees": 22,
            "county": "Nairobi",
            "email": "admin@kilimanihealth.co.ke",
            "user_name": "Dr. Brian Otieno",
            "user_email": "dr.otieno@kilimanihealth.co.ke",
            "title": "2026 Q1 Healthcare Compliance Assessment",
            "period": "2026 Q1",
            "date": date(2026, 3, 31),
            "response_func": lambda req: (
                AssessmentResponse.RESPONSE_NON_COMPLIANT if req.code in ["TAX-003", "TAX-004", "TAX-005", "DP-012", "DP-014"]
                else (AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT if req.code in ["EMP-011", "EMP-012", "DP-004"]
                else AssessmentResponse.RESPONSE_COMPLIANT)
            ),
        },
        # SME 3: High Risk (Rift Valley Produce)
        {
            "name": "Rift Valley Fresh Produce Ltd",
            "reg": "CPR/2019/33221",
            "pin": "P051332211A",
            "sector": "Agriculture & Agribusiness",
            "type": "Private Limited Company",
            "size": "Small (10-49)",
            "employees": 45,
            "county": "Nakuru",
            "email": "info@riftvalleyproduce.co.ke",
            "user_name": "Kiprono Koech",
            "user_email": "koech@riftvalleyproduce.co.ke",
            "title": "2026 Initial Compliance Baseline",
            "period": "Initial Baseline 2026",
            "date": date(2026, 3, 31),
            "response_func": lambda req: (
                AssessmentResponse.RESPONSE_NON_COMPLIANT if req.domain.code == "DATA_PROTECTION" or req.risk_weight >= 2.5
                else AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
            ),
        },
        # SME 4: Savanna Retail
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
            "user_name": "Hassan Ali",
            "user_email": "hassan@savannaretail.co.ke",
            "title": "2026 Q1 Wholesale Compliance Audit",
            "period": "2026 Q1",
            "date": date(2026, 3, 31),
            "response_func": lambda req: (
                AssessmentResponse.RESPONSE_COMPLIANT if req.domain.code == "TAX"
                else AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
            ),
        },
    ]

    for item in smes:
        org = Organization.query.filter_by(kra_pin=item["pin"]).first()
        if not org:
            org = Organization(
                name=item["name"],
                business_registration_number=item["reg"],
                kra_pin=item["pin"],
                industry_sector=item["sector"],
                business_type=item["type"],
                organization_size=item["size"],
                employee_count=item["employees"],
                county=item["county"],
                contact_email=item["email"],
                registration_date=date(2022, 1, 15),
                is_active=True,
            )
            db.session.add(org)
            db.session.flush()

            # Create default departments
            dept1 = Department(organization_id=org.id, name="Executive Management", code="EXEC")
            dept2 = Department(organization_id=org.id, name="Finance & Accounts", code="FIN")
            dept3 = Department(organization_id=org.id, name="Operations", code="OPS")
            db.session.add_all([dept1, dept2, dept3])
            db.session.flush()

            # Create User
            user = User.query.filter_by(email=item["user_email"]).first()
            if not user:
                user = User(
                    email=item["user_email"],
                    full_name=item["user_name"],
                    is_active=True,
                    is_verified=True,
                )
                user.set_password("CRAS@SME2026!")
                db.session.add(user)
                db.session.flush()

                if org_admin_role:
                    db.session.add(UserRole(user_id=user.id, role_id=org_admin_role.id))

            db.session.add(OrganizationUser(
                organization_id=org.id,
                user_id=user.id,
                role_id=org_admin_role.id,
                department_id=dept1.id,
                is_primary=True,
            ))

            # Seed statutory calendar deadlines
            seed_statutory_calendar_rules(org.id)

            # Create and score assessment
            assessment = ComplianceAssessment(
                organization_id=org.id,
                created_by_id=user.id,
                scoring_policy_version_id=version.id,
                title=item["title"],
                assessment_period=item["period"],
                assessment_date=item["date"],
                status=ComplianceAssessment.STATUS_COMPLETED,
            )
            db.session.add(assessment)
            db.session.flush()

            for req in all_reqs:
                resp_val = item["response_func"](req)
                resp = AssessmentResponse(
                    assessment_id=assessment.id,
                    requirement_id=req.id,
                    response_value=resp_val,
                    updated_by_id=user.id,
                )
                db.session.add(resp)
            db.session.flush()

            ScoringEngine.apply_and_persist_scores(assessment, version)
            ComplianceGapService.sync_gaps_for_assessment(assessment)

    db.session.commit()
    print("Synthetic SME scenarios seeded successfully.")

