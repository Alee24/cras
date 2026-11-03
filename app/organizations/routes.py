from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.base import db
from app.models.auth import Role
from app.models.organization import Organization, Department, OrganizationUser
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization, roles_required

organizations_bp = Blueprint("organizations", __name__, url_prefix="/organizations")


@organizations_bp.route("/profile")
@login_required
def profile():
    org = get_active_organization()
    if not org:
        flash("No active organization found.", "warning")
        return redirect(url_for("dashboard.index"))

    departments = Department.query.filter_by(organization_id=org.id).all()
    members = OrganizationUser.query.filter_by(organization_id=org.id).all()

    return render_template("organizations/profile.html", org=org, departments=departments, members=members)


@organizations_bp.route("/edit", methods=["GET", "POST"])
@login_required
@roles_required(Role.ORG_ADMIN)
def edit():
    org = get_active_organization()
    if not org:
        flash("No active organization found.", "warning")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        org.name = request.form.get("name", org.name).strip()
        org.employee_count = request.form.get("employee_count", org.employee_count, type=int)
        org.physical_address = request.form.get("physical_address", "").strip()
        org.county = request.form.get("county", org.county)
        org.contact_email = request.form.get("contact_email", org.contact_email).strip()
        org.phone_number = request.form.get("phone_number", "").strip()
        org.website = request.form.get("website", "").strip()

        db.session.commit()
        AuditService.log("UPDATE_ORGANIZATION", "Organization", org.id, {"name": org.name}, organization_id=org.id)
        flash("Organization profile updated successfully.", "success")
        return redirect(url_for("organizations.profile"))

    return render_template("organizations/edit.html", org=org)


@organizations_bp.route("/departments", methods=["GET", "POST"])
@login_required
@roles_required(Role.ORG_ADMIN)
def departments():
    org = get_active_organization()
    if not org:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        description = request.form.get("description", "").strip()

        if name:
            dept = Department(
                organization_id=org.id,
                name=name,
                code=code or None,
                description=description or None,
            )
            db.session.add(dept)
            db.session.commit()
            AuditService.log("CREATE_DEPARTMENT", "Department", dept.id, {"name": name}, organization_id=org.id)
            flash(f"Department '{name}' created successfully.", "success")

        return redirect(url_for("organizations.departments"))

    departments_list = Department.query.filter_by(organization_id=org.id).all()
    return render_template("organizations/departments.html", org=org, departments=departments_list)
