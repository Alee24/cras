from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.base import db, utcnow
from app.models.auth import Role, User
from app.models.organization import OrganizationUser
from app.models.compliance_management import CorrectiveAction, ComplianceGap
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.utils.decorators import get_active_organization, roles_required

corrective_actions_bp = Blueprint("corrective_actions", __name__, url_prefix="/corrective-actions")


@corrective_actions_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        flash("Please select an organization.", "warning")
        return redirect(url_for("dashboard.index"))

    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")

    query = CorrectiveAction.query.filter_by(organization_id=org.id)

    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)

    actions = query.order_by(CorrectiveAction.due_date.asc()).all()

    # Counts
    total_actions = CorrectiveAction.query.filter_by(organization_id=org.id).count()
    open_actions = CorrectiveAction.query.filter(
        CorrectiveAction.organization_id == org.id,
        CorrectiveAction.status.in_([CorrectiveAction.STATUS_OPEN, CorrectiveAction.STATUS_ASSIGNED, CorrectiveAction.STATUS_IN_PROGRESS])
    ).count()
    resolved_actions = CorrectiveAction.query.filter_by(
        organization_id=org.id, status=CorrectiveAction.STATUS_RESOLVED
    ).count()

    return render_template(
        "corrective_actions/index.html",
        org=org,
        actions=actions,
        total_actions=total_actions,
        open_actions=open_actions,
        resolved_actions=resolved_actions,
        current_status=status_filter,
        current_priority=priority_filter,
    )


@corrective_actions_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required(Role.ORG_ADMIN, Role.COMPLIANCE_OFFICER, Role.FINANCE_MANAGER, Role.HR_MANAGER)
def create():
    org = get_active_organization()
    gap_id = request.args.get("gap_id", type=int)
    gap = ComplianceGap.query.filter_by(id=gap_id, organization_id=org.id).first() if gap_id else None

    # Available users in organization for assignment
    org_users = [m.user for m in OrganizationUser.query.filter_by(organization_id=org.id).all()]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", CorrectiveAction.PRIORITY_HIGH)
        assigned_to_id = request.form.get("assigned_to_id", type=int)
        due_date_str = request.form.get("due_date")

        if not title or not description or not due_date_str:
            flash("Please provide a title, description, and target due date.", "danger")
            return render_template("corrective_actions/create.html", org=org, gap=gap, org_users=org_users)

        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            due_date = date.today()

        action = CorrectiveAction(
            organization_id=org.id,
            gap_id=gap.id if gap else None,
            assessment_id=gap.assessment_id if gap else None,
            requirement_id=gap.requirement_id if gap else None,
            title=title,
            action_description=description,
            priority=priority,
            status=CorrectiveAction.STATUS_ASSIGNED if assigned_to_id else CorrectiveAction.STATUS_OPEN,
            assigned_to_id=assigned_to_id if assigned_to_id else None,
            created_by_id=current_user.id,
            due_date=due_date,
        )
        db.session.add(action)

        # If linked to a gap, update gap status to ASSIGNED
        if gap and gap.status == ComplianceGap.STATUS_OPEN:
            gap.status = ComplianceGap.STATUS_ASSIGNED

        db.session.commit()

        # Notify assigned user
        if assigned_to_id:
            NotificationService.notify_user(
                user_id=assigned_to_id,
                title=f"New Corrective Action Assigned: {title}",
                message=f"You have been assigned a corrective action due by {due_date.strftime('%d %b %Y')}.",
                notification_type="ACTION",
                link_url=url_for("corrective_actions.view_action", action_id=action.id),
                org_id=org.id,
            )

        AuditService.log("CREATE_CORRECTIVE_ACTION", "CorrectiveAction", action.id, {"title": title, "assigned_to": assigned_to_id}, organization_id=org.id)

        flash(f"Corrective action '{title}' has been successfully created.", "success")
        return redirect(url_for("corrective_actions.index"))

    return render_template("corrective_actions/create.html", org=org, gap=gap, org_users=org_users)


@corrective_actions_bp.route("/<int:action_id>")
@login_required
def view_action(action_id):
    org = get_active_organization()
    action = CorrectiveAction.query.filter_by(id=action_id, organization_id=org.id).first_or_404()
    org_users = [m.user for m in OrganizationUser.query.filter_by(organization_id=org.id).all()]
    return render_template("corrective_actions/view.html", org=org, action=action, org_users=org_users)


@corrective_actions_bp.route("/<int:action_id>/update", methods=["POST"])
@login_required
def update_action(action_id):
    org = get_active_organization()
    action = CorrectiveAction.query.filter_by(id=action_id, organization_id=org.id).first_or_404()

    new_status = request.form.get("status")
    resolution_notes = request.form.get("resolution_notes", "").strip()
    assigned_to_id = request.form.get("assigned_to_id", type=int)

    if new_status:
        action.status = new_status
        if new_status in [CorrectiveAction.STATUS_RESOLVED, CorrectiveAction.STATUS_CLOSED]:
            action.completed_at = utcnow()
            # If linked to a gap, resolve gap
            if action.gap:
                action.gap.status = ComplianceGap.STATUS_RESOLVED
                action.gap.resolved_at = utcnow()
        else:
            action.completed_at = None

    if resolution_notes:
        action.resolution_notes = resolution_notes

    if assigned_to_id:
        action.assigned_to_id = assigned_to_id

    db.session.commit()

    AuditService.log("UPDATE_CORRECTIVE_ACTION", "CorrectiveAction", action.id, {"status": new_status}, organization_id=org.id)
    flash(f"Corrective action '{action.title}' updated successfully.", "success")
    return redirect(url_for("corrective_actions.view_action", action_id=action.id))

