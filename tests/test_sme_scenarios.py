import pytest
from datetime import date
from app.models.base import db
from app.models.auth import User
from app.models.organization import Organization
from app.models.regulatory import RegulatoryDomain, RegulatoryRequirement
from app.models.scoring import ScoringPolicyVersion
from app.models.assessment import ComplianceAssessment, AssessmentResponse
from app.services.scoring_service import ScoringEngine
from app.services.compliance_gap_service import ComplianceGapService


def test_scenario_1_apex_logistics_high_compliance(app):
    """
    SCENARIO 1: APEX LOGISTICS SOLUTIONS LTD
    Profile: Transport & Logistics SME, Nairobi, 35 employees.
    Posture: Well-managed governance.
    - All Data Protection requirements COMPLIANT (Ci = 1.0)
    - All Tax requirements COMPLIANT (Ci = 1.0)
    - All Labour requirements COMPLIANT (Ci = 1.0)
    
    Manual Calculation:
        W_dp = 0.35, C_dp = 1.0  => W_dp * C_dp = 0.35
        W_tax = 0.35, C_tax = 1.0 => W_tax * C_tax = 0.35
        W_lab = 0.30, C_lab = 1.0 => W_lab * C_lab = 0.30
        Composite Score = (0.35 + 0.35 + 0.30) * 100 = 100.00%
        Expected Classification: COMPLIANT (Green)
    """
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization.query.filter_by(kra_pin="P051992233M").first()
        if not org:
            org = Organization(
                name="Apex Logistics Solutions Ltd",
                business_registration_number="CPR/2020/88123",
                kra_pin="P051992233M",
                industry_sector="Transport & Logistics",
                business_type="Private Limited Company",
                organization_size="Small (10-49)",
                employee_count=35,
                county="Nairobi",
                contact_email="compliance@apexlogistics.co.ke",
            )
            db.session.add(org)

        user = User.query.filter_by(email="admin@apexlogistics.co.ke").first()
        if not user:
            user = User(email="admin@apexlogistics.co.ke", full_name="Grace Mwangi")
            user.set_password("ApexSecurePass2026!")
            db.session.add(user)
        db.session.flush()

        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=user.id,
            scoring_policy_version_id=version.id,
            title="Apex Logistics Annual Statutory Audit 2026",
            assessment_period="Annual 2026",
            assessment_date=date(2026, 3, 31),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment)
        db.session.flush()

        # All requirements COMPLIANT
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

        # Execute scoring engine
        result = ScoringEngine.apply_and_persist_scores(assessment, version)

        # Assertions
        assert result["overall_score"] == 100.0
        assert result["risk_classification"] == "COMPLIANT"
        assert result["compliant_count"] == len(all_reqs)
        assert result["non_compliant_count"] == 0
        assert result["partially_compliant_count"] == 0


def test_scenario_2_kilimani_health_moderate_risk(app):
    """
    SCENARIO 2: KILIMANI DIGITAL HEALTH CLINIC
    Profile: Healthcare & Healthtech SME, Nairobi, 22 employees.
    Posture:
    - Data Protection: High compliance (C_dp = 1.0)
    - Tax Compliance:
        eTIMS, PIN, TCC: Compliant (1.0)
        PAYE, Installment taxes: Non-Compliant (0.0) -> Ci ~ 0.55
    - Labour Compliance:
        Contracts & Leaves: Compliant (1.0)
        OSHA & WIBA: Partially Compliant (0.5) -> Ci ~ 0.75
        
    Manual Calculation:
        Expected overall score lands squarely in Moderate Risk (50.00% - 79.99%)
        Expected Classification: MODERATE_RISK (Amber)
    """
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization.query.filter_by(kra_pin="P052441122H").first()
        if not org:
            org = Organization(
                name="Kilimani Digital Health Clinic",
                business_registration_number="CPR/2022/44112",
                kra_pin="P052441122H",
                industry_sector="Healthcare & Pharmaceuticals",
                business_type="Private Limited Company",
                organization_size="Small (10-49)",
                employee_count=22,
                county="Nairobi",
                contact_email="admin@kilimanihealth.co.ke",
            )
            db.session.add(org)

        user = User.query.filter_by(email="dr.otieno@kilimanihealth.co.ke").first()
        if not user:
            user = User(email="dr.otieno@kilimanihealth.co.ke", full_name="Dr. Brian Otieno")
            user.set_password("HealthClinic2026!")
            db.session.add(user)
        db.session.flush()

        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=user.id,
            scoring_policy_version_id=version.id,
            title="Kilimani Health Q1 Compliance Review",
            assessment_period="2026 Q1",
            assessment_date=date(2026, 3, 31),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment)
        db.session.flush()

        all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).all()
        for req in all_reqs:
            if req.domain.code == "DATA_PROTECTION":
                # Some gaps: missing DPIA, missing vendor DPA, missing annual audit
                if req.code in ["DP-012", "DP-014", "DP-015", "DP-016"]:
                    val = AssessmentResponse.RESPONSE_NON_COMPLIANT
                elif req.code in ["DP-004", "DP-008"]:
                    val = AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
                else:
                    val = AssessmentResponse.RESPONSE_COMPLIANT
            elif req.domain.code == "TAX":
                # Arrears in corporate tax and PAYE
                if req.code in ["TAX-003", "TAX-004", "TAX-005", "TAX-009"]:
                    val = AssessmentResponse.RESPONSE_NON_COMPLIANT
                elif req.code in ["TAX-011", "TAX-012"]:
                    val = AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
                else:
                    val = AssessmentResponse.RESPONSE_COMPLIANT
            else: # LABOUR
                # OSHA & WIBA gaps
                if req.code in ["EMP-011", "EMP-012"]:
                    val = AssessmentResponse.RESPONSE_NON_COMPLIANT
                elif req.code in ["EMP-007", "EMP-013"]:
                    val = AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
                else:
                    val = AssessmentResponse.RESPONSE_COMPLIANT

            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req.id,
                response_value=val,
                updated_by_id=user.id,
            )
            db.session.add(resp)
        db.session.commit()

        result = ScoringEngine.apply_and_persist_scores(assessment, version)

        # Expected score ~ 50-79.99% (Moderate Risk)
        assert 50.0 <= result["overall_score"] <= 79.99
        assert result["risk_classification"] == "MODERATE_RISK"


def test_scenario_3_rift_valley_produce_high_risk(app):
    """
    SCENARIO 3: RIFT VALLEY FRESH PRODUCE LTD
    Profile: Agribusiness SME, Nakuru, 45 employees.
    Posture:
    - Data Protection: Complete absence of ODPC registration, policies, training (All Non-Compliant: 0.0)
    - Tax Compliance: Multiple late filings & lack of eTIMS (Mostly Non-Compliant: Ci ~ 0.30)
    - Labour: Non-compliant with OSHA & WIBA, minimum wage disputes (Ci ~ 0.40)
    
    Manual Calculation:
        W_dp * C_dp = 0.35 * 0.0 = 0.0
        W_tax * C_tax = 0.35 * 0.30 = 0.105
        W_lab * C_lab = 0.30 * 0.40 = 0.120
        Composite Score = (0.0 + 0.105 + 0.120) * 100 = 22.50%
        Expected Classification: HIGH_RISK (Red) (< 50%)
    """
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization.query.filter_by(kra_pin="P051332211A").first()
        if not org:
            org = Organization(
                name="Rift Valley Fresh Produce Ltd",
                business_registration_number="CPR/2019/33221",
                kra_pin="P051332211A",
                industry_sector="Agriculture & Agribusiness",
                business_type="Private Limited Company",
                organization_size="Small (10-49)",
                employee_count=45,
                county="Nakuru",
                contact_email="info@riftvalleyproduce.co.ke",
            )
            db.session.add(org)

        user = User.query.filter_by(email="manager@riftvalleyproduce.co.ke").first()
        if not user:
            user = User(email="manager@riftvalleyproduce.co.ke", full_name="Kiprono Koech")
            user.set_password("AgroProduce2026!")
            db.session.add(user)
        db.session.flush()

        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=user.id,
            scoring_policy_version_id=version.id,
            title="Rift Valley Produce Baseline Assessment",
            assessment_period="Initial Baseline 2026",
            assessment_date=date(2026, 3, 31),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment)
        db.session.flush()

        all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).all()
        for req in all_reqs:
            if req.domain.code == "DATA_PROTECTION":
                val = AssessmentResponse.RESPONSE_NON_COMPLIANT
            elif req.domain.code == "TAX":
                val = AssessmentResponse.RESPONSE_NON_COMPLIANT if req.risk_weight >= 2.0 else AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT
            else: # LABOUR
                val = AssessmentResponse.RESPONSE_NON_COMPLIANT if req.risk_weight >= 2.5 else AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT

            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req.id,
                response_value=val,
                updated_by_id=user.id,
            )
            db.session.add(resp)
        db.session.commit()

        result = ScoringEngine.apply_and_persist_scores(assessment, version)

        assert result["overall_score"] < 50.0
        assert result["risk_classification"] == "HIGH_RISK"

        # Check gap generation
        gaps_count = ComplianceGapService.sync_gaps_for_assessment(assessment)
        assert gaps_count > 0


def test_scenario_4_savanna_retail_exact_threshold(app):
    """
    SCENARIO 4: SAVANNA RETAIL DISTRIBUTORS LTD
    Profile: Wholesale & Retail SME, Mombasa, 18 employees.
    Posture: Tested for exact threshold mathematical precision.
    """
    with app.app_context():
        version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        org = Organization.query.filter_by(kra_pin="P053110992R").first()
        if not org:
            org = Organization(
                name="Savanna Retail Distributors Ltd",
                business_registration_number="CPR/2023/11099",
                kra_pin="P053110992R",
                industry_sector="Retail & Wholesale",
                business_type="Private Limited Company",
                employee_count=18,
                county="Mombasa",
                contact_email="admin@savannaretail.co.ke",
            )
            db.session.add(org)

        user = User.query.filter_by(email="hassan@savannaretail.co.ke").first()
        if not user:
            user = User(email="hassan@savannaretail.co.ke", full_name="Hassan Ali")
            user.set_password("SavannaRetail2026!")
            db.session.add(user)
        db.session.flush()

        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=user.id,
            scoring_policy_version_id=version.id,
            title="Savanna Retail Q1 Compliance Audit",
            assessment_period="2026 Q1",
            assessment_date=date(2026, 3, 31),
            status=ComplianceAssessment.STATUS_DRAFT,
        )
        db.session.add(assessment)
        db.session.flush()

        # All responses PARTIALLY_COMPLIANT (Factor = 0.5 for all items)
        # Expected composite score = (0.35 * 0.5 + 0.35 * 0.5 + 0.30 * 0.5) * 100 = 50.00%
        # Threshold: 50.00% is the exact boundary for MODERATE_RISK!
        all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).all()
        for req in all_reqs:
            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req.id,
                response_value=AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT,
                updated_by_id=user.id,
            )
            db.session.add(resp)
        db.session.commit()

        result = ScoringEngine.apply_and_persist_scores(assessment, version)

        # Must be exactly 50.00% and classified as MODERATE_RISK
        assert result["overall_score"] == 50.0
        assert result["risk_classification"] == "MODERATE_RISK"
