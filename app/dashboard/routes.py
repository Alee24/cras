from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_login import login_required, current_user
from app.models.base import db
from app.models.assessment import ComplianceAssessment, AssessmentDomainScore, AssessmentResponse
from app.models.compliance_management import ComplianceGap, CorrectiveAction, ComplianceDeadline
from app.models.regulatory import RegulatoryDomain
from app.utils.decorators import get_active_organization

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        # User has no organization assigned yet
        return render_template("dashboard/empty.html")

    # Filter by period if requested
    period_filter = request.args.get("period")
    
    query = ComplianceAssessment.query.filter_by(organization_id=org.id)
    if period_filter:
        query = query.filter_by(assessment_period=period_filter)

    # Get latest completed or submitted assessment
    latest_assessment = query.filter(
        ComplianceAssessment.status.in_([ComplianceAssessment.STATUS_COMPLETED, ComplianceAssessment.STATUS_SUBMITTED])
    ).order_by(ComplianceAssessment.assessment_date.desc(), ComplianceAssessment.id.desc()).first()

    # If no completed assessment, get latest draft
    if not latest_assessment:
        latest_assessment = ComplianceAssessment.query.filter_by(organization_id=org.id).order_by(
            ComplianceAssessment.id.desc()
        ).first()

    # Total obligations in system
    all_domains = RegulatoryDomain.query.filter_by(is_active=True).all()
    domain_scores = []
    
    overall_score = 0.0
    risk_classification = "NOT_CLASSIFIED"
    total_obligations = 0
    compliant_count = 0
    partially_compliant_count = 0
    non_compliant_count = 0
    not_applicable_count = 0

    if latest_assessment:
        overall_score = latest_assessment.overall_score or 0.0
        risk_classification = latest_assessment.risk_classification or "NOT_CLASSIFIED"
        total_obligations = latest_assessment.total_obligations
        compliant_count = latest_assessment.compliant_count
        partially_compliant_count = latest_assessment.partially_compliant_count
        non_compliant_count = latest_assessment.non_compliant_count
        not_applicable_count = latest_assessment.not_applicable_count

        domain_scores = AssessmentDomainScore.query.filter_by(assessment_id=latest_assessment.id).all()

    # Pending Assessments count
    pending_assessments_count = ComplianceAssessment.query.filter_by(
        organization_id=org.id, status=ComplianceAssessment.STATUS_DRAFT
    ).count()

    # Open Corrective Actions
    open_actions_count = CorrectiveAction.query.filter(
        CorrectiveAction.organization_id == org.id,
        CorrectiveAction.status.in_([CorrectiveAction.STATUS_OPEN, CorrectiveAction.STATUS_ASSIGNED, CorrectiveAction.STATUS_IN_PROGRESS])
    ).count()

    # Overdue Compliance Deadlines
    today = date.today()
    overdue_deadlines_count = ComplianceDeadline.query.filter(
        ComplianceDeadline.organization_id == org.id,
        ComplianceDeadline.status != ComplianceDeadline.STATUS_COMPLETED,
        ComplianceDeadline.current_due_date < today
    ).count()

    # Open Compliance Gaps
    open_gaps_count = ComplianceGap.query.filter(
        ComplianceGap.organization_id == org.id,
        ComplianceGap.status.in_([ComplianceGap.STATUS_OPEN, ComplianceGap.STATUS_ASSIGNED, ComplianceGap.STATUS_IN_PROGRESS])
    ).count()

    # Upcoming Deadlines (next 5)
    upcoming_deadlines = ComplianceDeadline.query.filter(
        ComplianceDeadline.organization_id == org.id,
        ComplianceDeadline.is_active == True,
    ).order_by(ComplianceDeadline.current_due_date.asc()).limit(5).all()

    # Compliance trend (last 6 completed assessments)
    trend_assessments = ComplianceAssessment.query.filter(
        ComplianceAssessment.organization_id == org.id,
        ComplianceAssessment.overall_score.isnot(None)
    ).order_by(ComplianceAssessment.assessment_date.asc()).limit(6).all()

    trend_labels = [a.assessment_period for a in trend_assessments]
    trend_scores = [round(a.overall_score, 1) for a in trend_assessments]

    # Available assessment periods for filter dropdown
    available_periods = [row[0] for row in db.session.query(ComplianceAssessment.assessment_period).filter_by(
        organization_id=org.id
    ).distinct().all()]

    return render_template(
        "dashboard/index.html",
        org=org,
        latest_assessment=latest_assessment,
        overall_score=overall_score,
        risk_classification=risk_classification,
        total_obligations=total_obligations,
        compliant_count=compliant_count,
        partially_compliant_count=partially_compliant_count,
        non_compliant_count=non_compliant_count,
        not_applicable_count=not_applicable_count,
        domain_scores=domain_scores,
        pending_assessments_count=pending_assessments_count,
        open_actions_count=open_actions_count,
        overdue_deadlines_count=overdue_deadlines_count,
        open_gaps_count=open_gaps_count,
        upcoming_deadlines=upcoming_deadlines,
        trend_labels=trend_labels,
        trend_scores=trend_scores,
        available_periods=available_periods,
        current_period=period_filter,
    )
