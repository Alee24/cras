from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, Department, OrganizationUser
from app.auth.forms import LoginForm, RegisterForm, ChangePasswordForm, ProfileForm
from app.services.audit_service import AuditService
from app.services.seed_data import seed_statutory_calendar_rules

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Invalid email address or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash("Your account has been deactivated. Please contact your organization administrator or CRAS support.", "warning")
            return render_template("auth/login.html", form=form)

        if user.is_locked:
            flash(f"Account locked due to excessive failed attempts. Please retry after {user.locked_until.strftime('%H:%M:%S UTC')}.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.check_password(password):
            user.record_failed_login()
            db.session.commit()
            AuditService.log("LOGIN_FAILED", "User", user.id, {"reason": "Incorrect password", "email": email}, user_id=user.id)
            attempts_left = max(0, 5 - user.failed_login_attempts)
            if attempts_left > 0:
                flash(f"Invalid email address or password. ({attempts_left} attempts remaining before temporary lockout)", "danger")
            else:
                flash("Account has been temporarily locked due to 5 consecutive failed attempts. Please retry in 15 minutes.", "danger")
            return render_template("auth/login.html", form=form)

        # Successful login
        user.record_successful_login()
        db.session.commit()

        login_user(user, remember=form.remember_me.data)

        # Set default active organization in session
        if user.organization_memberships:
            session["active_org_id"] = user.organization_memberships[0].organization_id
        elif user.is_super_admin:
            first_org = Organization.query.first()
            if first_org:
                session["active_org_id"] = first_org.id

        AuditService.log("LOGIN_SUCCESS", "User", user.id, {"email": email}, user_id=user.id, organization_id=session.get("active_org_id"))

        flash(f"Welcome back, {user.full_name}!", "success")
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            # 1. Create User
            user = User(
                email=form.email.data.strip().lower(),
                full_name=form.full_name.data.strip(),
                phone_number=form.phone_number.data.strip(),
                is_active=True,
                is_verified=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()

            # 2. Create Organization
            org = Organization(
                name=form.organization_name.data.strip(),
                business_registration_number=form.business_registration_number.data.strip().upper(),
                kra_pin=form.kra_pin.data.strip().upper(),
                industry_sector=form.industry_sector.data,
                business_type=form.business_type.data,
                organization_size=form.organization_size.data,
                employee_count=form.employee_count.data,
                county=form.county.data,
                contact_email=user.email,
                phone_number=user.phone_number,
                registration_date=date.today(),
                is_active=True,
            )
            db.session.add(org)
            db.session.flush()

            # 3. Create Default Departments
            depts = [
                Department(organization_id=org.id, name="Executive Management", code="EXEC"),
                Department(organization_id=org.id, name="Finance & Accounts", code="FIN"),
                Department(organization_id=org.id, name="Human Resources", code="HR"),
                Department(organization_id=org.id, name="Operations & IT", code="OPS"),
            ]
            db.session.add_all(depts)
            db.session.flush()

            # 4. Assign ORG_ADMIN Role to User
            admin_role = Role.query.filter_by(name=Role.ORG_ADMIN).first()
            if not admin_role:
                admin_role = Role(name=Role.ORG_ADMIN, display_name="Organization Administrator")
                db.session.add(admin_role)
                db.session.flush()

            user_role = UserRole(user_id=user.id, role_id=admin_role.id)
            db.session.add(user_role)

            org_user = OrganizationUser(
                organization_id=org.id,
                user_id=user.id,
                role_id=admin_role.id,
                department_id=depts[0].id,
                is_primary=True,
            )
            db.session.add(org_user)

            # 5. Seed default statutory deadlines for Kenya SME
            seed_statutory_calendar_rules(org.id)

            db.session.commit()

            # 6. Auto-login
            login_user(user)
            session["active_org_id"] = org.id

            AuditService.log("REGISTER_SME", "Organization", org.id, {"org_name": org.name, "user_email": user.email}, user_id=user.id, organization_id=org.id)

            flash(f"Account for {org.name} successfully created! You are now logged in as Organization Administrator.", "success")
            return redirect(url_for("dashboard.index"))

        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed due to a system error: {str(e)}", "danger")

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    AuditService.log("LOGOUT", "User", current_user.id, {"email": current_user.email}, user_id=current_user.id, organization_id=session.get("active_org_id"))
    logout_user()
    session.pop("active_org_id", None)
    flash("You have been securely signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/switch-org/<int:org_id>")
@login_required
def switch_org(org_id):
    """Switches the active organization tenant in the current session."""
    if current_user.is_super_admin:
        org = Organization.query.get_or_404(org_id)
        session["active_org_id"] = org.id
        flash(f"Switched active organization to: {org.name}", "info")
    else:
        membership = OrganizationUser.query.filter_by(user_id=current_user.id, organization_id=org_id).first()
        if not membership:
            flash("You do not have access to this organization.", "danger")
            return redirect(url_for("dashboard.index"))
        session["active_org_id"] = membership.organization_id
        flash(f"Switched active organization to: {membership.organization.name}", "info")

    AuditService.log("SWITCH_ORGANIZATION", "Organization", org_id, {}, user_id=current_user.id, organization_id=org_id)
    return redirect(request.referrer or url_for("dashboard.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if form.validate_on_submit() and "submit" in request.form and request.form.get("submit") == "Save Profile Changes":
        current_user.full_name = form.full_name.data.strip()
        current_user.phone_number = form.phone_number.data.strip() if form.phone_number.data else None
        db.session.commit()
        AuditService.log("UPDATE_PROFILE", "User", current_user.id, {"full_name": current_user.full_name}, user_id=current_user.id)
        flash("Your profile details have been updated successfully.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, password_form=password_form)


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Incorrect current password.", "danger")
            return render_template("auth/profile.html", form=form, password_form=password_form)

        current_user.set_password(password_form.new_password.data)
        db.session.commit()
        AuditService.log("CHANGE_PASSWORD", "User", current_user.id, {}, user_id=current_user.id)
        flash("Your password has been changed successfully.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, password_form=password_form)

