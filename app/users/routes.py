from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import OrganizationUser, Department
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization, roles_required

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
@login_required
@roles_required(Role.ORG_ADMIN)
def index():
    org = get_active_organization()
    if not org:
        return redirect(url_for("dashboard.index"))

    memberships = OrganizationUser.query.filter_by(organization_id=org.id).all()
    roles = Role.query.filter(Role.name != Role.SUPER_ADMIN).all()
    departments = Department.query.filter_by(organization_id=org.id).all()

    return render_template(
        "users/index.html",
        org=org,
        memberships=memberships,
        roles=roles,
        departments=departments,
    )


@users_bp.route("/add", methods=["POST"])
@login_required
@roles_required(Role.ORG_ADMIN)
def add_user():
    org = get_active_organization()
    email = request.form.get("email", "").strip().lower()
    full_name = request.form.get("full_name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    role_id = request.form.get("role_id", type=int)
    department_id = request.form.get("department_id", type=int)
    password = request.form.get("password", "CRAS@Kenya2026!")

    if not email or not full_name or not role_id:
        flash("Email, full name, and role are required.", "danger")
        return redirect(url_for("users.index"))

    # Check if user already exists
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            phone_number=phone_number or None,
            is_active=True,
            is_verified=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

    # Check if user is already a member of this org
    existing_member = OrganizationUser.query.filter_by(organization_id=org.id, user_id=user.id).first()
    if existing_member:
        flash("This user is already a member of your organization.", "warning")
        return redirect(url_for("users.index"))

    # Add organization membership
    membership = OrganizationUser(
        organization_id=org.id,
        user_id=user.id,
        role_id=role_id,
        department_id=department_id if department_id else None,
        is_primary=False,
    )
    db.session.add(membership)

    # Ensure role is in user_roles
    if not UserRole.query.filter_by(user_id=user.id, role_id=role_id).first():
        db.session.add(UserRole(user_id=user.id, role_id=role_id))

    db.session.commit()

    AuditService.log("ADD_ORG_USER", "OrganizationUser", membership.id, {"user_email": email, "role_id": role_id}, organization_id=org.id)
    flash(f"User '{full_name}' ({email}) has been added to the organization.", "success")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:membership_id>/toggle-status", methods=["POST"])
@login_required
@roles_required(Role.ORG_ADMIN)
def toggle_status(membership_id):
    org = get_active_organization()
    membership = OrganizationUser.query.filter_by(id=membership_id, organization_id=org.id).first_or_404()

    if membership.user_id == current_user.id:
        flash("You cannot deactivate your own administrative account.", "danger")
        return redirect(url_for("users.index"))

    target_user = membership.user
    target_user.is_active = not target_user.is_active
    db.session.commit()

    AuditService.log("TOGGLE_USER_STATUS", "User", target_user.id, {"is_active": target_user.is_active}, organization_id=org.id)
    status_str = "activated" if target_user.is_active else "deactivated"
    flash(f"User {target_user.full_name} has been {status_str}.", "info")
    return redirect(url_for("users.index"))

