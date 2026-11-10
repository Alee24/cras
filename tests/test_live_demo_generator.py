from app.models.organization import Organization
from app.models.assessment import ComplianceAssessment, AssessmentEvidence
from app.models.compliance_management import ComplianceGap, CorrectiveAction, ComplianceDeadline
from app.services.live_demo_generator import populate_comprehensive_live_data


def test_populate_live_demo_generator(app, client):
    """Verifies that the live demonstration generator seeds all 4 SME companies with realistic multi-period data."""
    with app.app_context():
        stats = populate_comprehensive_live_data(upload_folder=app.config["UPLOAD_FOLDER"])

        assert stats["status"] == "success"
        assert stats["organizations"] >= 4
        assert stats["assessments"] >= 16
        assert stats["gaps"] > 0
        assert stats["actions"] > 0
        assert stats["calendar_events"] >= 20
        assert stats["evidence_files"] >= 4

        # Verify Apex Logistics Solutions exists and is compliant
        apex = Organization.query.filter_by(name="Apex Logistics Solutions Ltd").first()
        assert apex is not None
        assert apex.kra_pin == "P051992233M"

        # Verify Kilimani Digital Health Clinic exists
        kilimani = Organization.query.filter_by(name="Kilimani Digital Health Clinic").first()
        assert kilimani is not None

        # Verify multi-period assessments exist for Apex Logistics
        apex_assessments = ComplianceAssessment.query.filter_by(organization_id=apex.id).all()
        assert len(apex_assessments) >= 4
        periods = {a.assessment_period for a in apex_assessments}
        assert "2025 Q3" in periods
        assert "2025 Q4" in periods
        assert "2026 Q1" in periods

        # Verify evidence files exist
        evidence_records = AssessmentEvidence.query.filter_by(organization_id=apex.id).all()
        assert len(evidence_records) > 0
        for ev in evidence_records:
            assert ev.verification_status == AssessmentEvidence.STATUS_VERIFIED
            assert ev.stored_filename is not None
