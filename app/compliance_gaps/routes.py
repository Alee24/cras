from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.base import db, utcnow
from app.models.auth import Role
from app.models.compliance_management import ComplianceGap, CorrectiveAction
from app.models.regulatory import RegulatoryDomain
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization, roles_required

compliance_gaps_bp = Blueprint("compliance_gaps", __name__, url_prefix="/compliance-gaps")


@compliance_gaps_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        flash("Please select an organization.", "warning")
        return redirect(url_for("dashboard.index"))

    # Filters
    status_filter = request.args.get("status")
    severity_filter = request.args.get("severity")
    domain_filter = request.args.get("domain")

    query = ComplianceGap.query.filter_by(organization_id=org.id)

    if status_filter:
        query = query.filter_by(status=status_filter)
    if severity_filter:
        query = query.filter_by(severity=severity_filter)
    if domain_filter:
        query = query.join(RegulatoryDomain).filter(RegulatoryDomain.code == domain_filter)

    gaps = query.order_by(ComplianceGap.severity.asc(), ComplianceGap.identified_at.desc()).all()
    domains = RegulatoryDomain.query.filter_by(is_active=True).all()

    # Counts
    total_gaps = ComplianceGap.query.filter_by(organization_id=org.id).count()
    open_gaps = ComplianceGap.query.filter(
        ComplianceGap.organization_id == org.id,
        ComplianceGap.status.in_([ComplianceGap.STATUS_OPEN, ComplianceGap.STATUS_ASSIGNED, ComplianceGap.STATUS_IN_PROGRESS])
    ).count()
    critical_gaps = ComplianceGap.query.filter_by(
        organization_id=org.id, severity=ComplianceGap.SEVERITY_CRITICAL
    ).count()
    resolved_gaps = ComplianceGap.query.filter_by(
        organization_id=org.id, status=ComplianceGap.STATUS_RESOLVED
    ).count()

    return render_template(
        "compliance_gaps/index.html",
        org=org,
        gaps=gaps,
        domains=domains,
        total_gaps=total_gaps,
        open_gaps=open_gaps,
        critical_gaps=critical_gaps,
        resolved_gaps=resolved_gaps,
        current_status=status_filter,
        current_severity=severity_filter,
        current_domain=domain_filter,
    )


@compliance_gaps_bp.route("/<int:gap_id>")
@login_required
def view_gap(gap_id):
    org = get_active_organization()
    gap = ComplianceGap.query.filter_by(id=gap_id, organization_id=org.id).first_or_404()
    actions = CorrectiveAction.query.filter_by(gap_id=gap.id).all()
    return render_template("compliance_gaps/view.html", org=org, gap=gap, actions=actions)


@compliance_gaps_bp.route("/<int:gap_id>/update-status", methods=["POST"])
@login_required
@roles_required(Role.ORG_ADMIN, Role.COMPLIANCE_OFFICER, Role.FINANCE_MANAGER, Role.HR_MANAGER)
def update_status(gap_id):
    org = get_active_organization()
    gap = ComplianceGap.query.filter_by(id=gap_id, organization_id=org.id).first_or_404()

    new_status = request.form.get("status")
    if new_status in [ComplianceGap.STATUS_OPEN, ComplianceGap.STATUS_ASSIGNED, ComplianceGap.STATUS_IN_PROGRESS, ComplianceGap.STATUS_RESOLVED, ComplianceGap.STATUS_CLOSED]:
        gap.status = new_status
        if new_status in [ComplianceGap.STATUS_RESOLVED, ComplianceGap.STATUS_CLOSED]:
            gap.resolved_at = utcnow()
        else:
            gap.resolved_at = None
        db.session.commit()

        AuditService.log("UPDATE_GAP_STATUS", "ComplianceGap", gap.id, {"new_status": new_status}, organization_id=org.id)
        flash(f"Compliance Gap status updated to '{new_status}'.", "success")

    return redirect(url_for("compliance_gaps.view_gap", gap_id=gap.id))

