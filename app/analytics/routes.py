from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models.base import db
from app.models.assessment import ComplianceAssessment, AssessmentDomainScore, AssessmentResponse
from app.models.compliance_management import ComplianceGap, CorrectiveAction
from app.models.regulatory import RegulatoryDomain
from app.utils.decorators import get_active_organization

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        return render_template("dashboard/empty.html")

    # Historical assessments for timeline
    assessments = ComplianceAssessment.query.filter_by(organization_id=org.id).order_by(
        ComplianceAssessment.assessment_date.asc()
    ).all()

    # Latest completed assessment for current distribution
    latest = ComplianceAssessment.query.filter_by(
        organization_id=org.id, status=ComplianceAssessment.STATUS_COMPLETED
    ).order_by(ComplianceAssessment.assessment_date.desc(), ComplianceAssessment.id.desc()).first()

    # Domains
    domains = RegulatoryDomain.query.filter_by(is_active=True).all()
    domain_scores_map = {}
    if latest:
        for ds in latest.domain_scores:
            domain_scores_map[ds.domain.code] = {
                "title": ds.domain.title,
                "score": round(ds.normalized_score * 100, 1),
                "classification": ds.classification,
                "weight": int(ds.domain_weight * 100),
                "compliant": ds.compliant_count,
                "partially": ds.partially_compliant_count,
                "non_compliant": ds.non_compliant_count,
            }

    # Gaps severity count
    gap_stats = {
        "CRITICAL": ComplianceGap.query.filter_by(organization_id=org.id, severity="CRITICAL").count(),
        "HIGH": ComplianceGap.query.filter_by(organization_id=org.id, severity="HIGH").count(),
        "MEDIUM": ComplianceGap.query.filter_by(organization_id=org.id, severity="MEDIUM").count(),
        "LOW": ComplianceGap.query.filter_by(organization_id=org.id, severity="LOW").count(),
    }

    # Action status count
    action_stats = {
        "OPEN": CorrectiveAction.query.filter_by(organization_id=org.id, status=CorrectiveAction.STATUS_OPEN).count(),
        "IN_PROGRESS": CorrectiveAction.query.filter_by(organization_id=org.id, status=CorrectiveAction.STATUS_IN_PROGRESS).count(),
        "RESOLVED": CorrectiveAction.query.filter_by(organization_id=org.id, status=CorrectiveAction.STATUS_RESOLVED).count(),
        "CLOSED": CorrectiveAction.query.filter_by(organization_id=org.id, status=CorrectiveAction.STATUS_CLOSED).count(),
    }

    return render_template(
        "analytics/index.html",
        org=org,
        latest=latest,
        assessments=assessments,
        domain_scores_map=domain_scores_map,
        gap_stats=gap_stats,
        action_stats=action_stats,
    )

