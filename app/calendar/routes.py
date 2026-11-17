from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.base import db, utcnow
from app.models.auth import Role
from app.models.compliance_management import ComplianceDeadline
from app.models.regulatory import RegulatoryDomain
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization, roles_required

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@calendar_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        flash("Please select an organization.", "warning")
        return redirect(url_for("dashboard.index"))

    today = date.today()
    status_filter = request.args.get("status")

    # Refresh deadline cycle statuses dynamically
    org_deadlines = ComplianceDeadline.query.filter_by(organization_id=org.id, is_active=True).all()
    status_changed = False
    for d in org_deadlines:
        old_status = d.status
        d.refresh_status_for_date(today)
        if d.status != old_status:
            status_changed = True
    if status_changed:
        db.session.commit()

    query = ComplianceDeadline.query.filter_by(organization_id=org.id, is_active=True)
    if status_filter:
        query = query.filter_by(status=status_filter)

    deadlines = query.order_by(ComplianceDeadline.current_due_date.asc()).all()

    # Upcoming within 30 days
    in_30_days = today + timedelta(days=30)
    upcoming_30 = ComplianceDeadline.query.filter(
        ComplianceDeadline.organization_id == org.id,
        ComplianceDeadline.current_due_date >= today,
        ComplianceDeadline.current_due_date <= in_30_days,
        ComplianceDeadline.status != ComplianceDeadline.STATUS_COMPLETED
    ).count()

    overdue_count = ComplianceDeadline.query.filter_by(
        organization_id=org.id, status=ComplianceDeadline.STATUS_OVERDUE
    ).count()

    domains = RegulatoryDomain.query.filter_by(is_active=True).all()

    return render_template(
        "calendar/index.html",
        org=org,
        deadlines=deadlines,
        domains=domains,
        today=today,
        upcoming_30=upcoming_30,
        overdue_count=overdue_count,
        current_status=status_filter,
    )


@calendar_bp.route("/new", methods=["POST"])
@login_required
@roles_required(Role.ORG_ADMIN, Role.COMPLIANCE_OFFICER, Role.FINANCE_MANAGER, Role.HR_MANAGER)
def create_deadline():
    org = get_active_organization()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    statutory_rule = request.form.get("statutory_rule", "").strip()
    domain_id = request.form.get("domain_id", type=int)
    due_date_str = request.form.get("due_date")
    recurrence = request.form.get("recurrence", ComplianceDeadline.RECURRENCE_MONTHLY)
    reminder_days = request.form.get("reminder_days", 5, type=int)

    if not title or not due_date_str:
        flash("Please provide deadline title and target due date.", "danger")
        return redirect(url_for("calendar.index"))

    try:
        due_date = date.fromisoformat(due_date_str)
    except ValueError:
        due_date = date.today()

    deadline = ComplianceDeadline(
        organization_id=org.id,
        domain_id=domain_id if domain_id else None,
        title=title,
        description=description,
        statutory_rule=statutory_rule,
        deadline_type="INTERNAL" if not statutory_rule else "STATUTORY_RECURRING",
        recurrence=recurrence,
        current_due_date=due_date,
        reminder_days_before=reminder_days,
        status=ComplianceDeadline.STATUS_PENDING,
        is_active=True,
    )
    db.session.add(deadline)
    db.session.commit()

    AuditService.log("CREATE_DEADLINE", "ComplianceDeadline", deadline.id, {"title": title, "due_date": str(due_date)}, organization_id=org.id)
    flash(f"Compliance deadline '{title}' added to calendar.", "success")
    return redirect(url_for("calendar.index"))


@calendar_bp.route("/<int:deadline_id>/toggle-complete", methods=["POST"])
@login_required
def toggle_complete(deadline_id):
    org = get_active_organization()
    deadline = ComplianceDeadline.query.filter_by(id=deadline_id, organization_id=org.id).first_or_404()

    if deadline.status == ComplianceDeadline.STATUS_COMPLETED:
        deadline.reopen_previous_cycle()
        db.session.commit()
        AuditService.log("REOPEN_DEADLINE", "ComplianceDeadline", deadline.id, {
            "title": deadline.title,
            "restored_due_date": str(deadline.current_due_date),
            "status": deadline.status
        }, organization_id=org.id)
        flash(f"Deadline '{deadline.title}' reopened for {deadline.current_due_date.strftime('%d %b %Y')}.", "info")
    else:
        prev_date = deadline.current_due_date
        deadline.advance_to_next_cycle()
        db.session.commit()
        AuditService.log("COMPLETE_DEADLINE", "ComplianceDeadline", deadline.id, {
            "title": deadline.title,
            "completed_cycle_due_date": str(prev_date),
            "next_due_date": str(deadline.current_due_date),
            "status": deadline.status
        }, organization_id=org.id)
        if deadline.recurrence == ComplianceDeadline.RECURRENCE_ANNUAL:
            flash(
                f"Statutory filing '{deadline.title}' completed for {prev_date.year}! Status remains COMPLETED for {prev_date.year}. Next filing deadline updated to {deadline.current_due_date.strftime('%d %b %Y')}.",
                "success"
            )
        elif deadline.recurrence == ComplianceDeadline.RECURRENCE_MONTHLY:
            flash(
                f"Statutory return '{deadline.title}' marked as filed! Status remains COMPLETED for {prev_date.strftime('%B %Y')}. Next filing deadline updated to {deadline.current_due_date.strftime('%d %b %Y')}.",
                "success"
            )
        else:
            flash(f"Compliance obligation '{deadline.title}' marked as completed!", "success")
    return redirect(url_for("calendar.index"))
