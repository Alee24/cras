from functools import wraps
from flask import abort, redirect, url_for, flash, session, request
from flask_login import current_user
from app.models.auth import Role
from app.models.organization import Organization, OrganizationUser


def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_super_admin:
            flash("Access denied: Super Administrator privileges are required for this action.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    """
    Checks if current user has any of the allowed roles, either globally or within the active organization.
    Super Admins are always allowed.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.url))
            
            if current_user.is_super_admin:
                return f(*args, **kwargs)

            active_org_id = session.get("active_org_id")
            user_role = current_user.get_role_in_org(active_org_id) if active_org_id else None

            # Also check user_roles directly
            has_role = (user_role in allowed_roles) or any(ur.role.name in allowed_roles for ur in current_user.user_roles)

            if not has_role:
                flash("Access denied: You do not have sufficient permissions to access this feature.", "danger")
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_active_organization() -> Organization:
    """
    Helper function to get current user's active organization from session,
    or default to their primary organization. Enforces strict tenant isolation.
    """
    if not current_user.is_authenticated:
        return None

    active_org_id = session.get("active_org_id")
    if active_org_id:
        # Verify user still belongs to this org, or is super admin
        if current_user.is_super_admin:
            return Organization.query.get(active_org_id)
        membership = OrganizationUser.query.filter_by(user_id=current_user.id, organization_id=active_org_id).first()
        if membership:
            return membership.organization

    # Fallback to user's first available organization
    membership = OrganizationUser.query.filter_by(user_id=current_user.id).first()
    if membership:
        session["active_org_id"] = membership.organization_id
        return membership.organization

    # If super admin with no orgs assigned, select first org in system if exists
    if current_user.is_super_admin:
        org = Organization.query.first()
        if org:
            session["active_org_id"] = org.id
            return org

    return None
