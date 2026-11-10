import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.base import db
from app.models.auth import Role, User
from app.models.organization import Organization
from app.models.regulatory import RegulatoryDomain, RegulatoryCategory, RegulatoryRequirement
from app.models.scoring import ScoringPolicy, ScoringPolicyVersion
from app.models.audit_and_notification import AuditLog, SystemSetting
from app.services.audit_service import AuditService
from app.services.live_demo_generator import populate_comprehensive_live_data
from app.utils.decorators import super_admin_required, get_active_organization

admin_bp = Blueprint("administration", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@super_admin_required
def index():
    org = get_active_organization()
    total_orgs = Organization.query.count()
    total_users = User.query.count()
    total_requirements = RegulatoryRequirement.query.count()
    total_audit_logs = AuditLog.query.count()

    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    orgs = Organization.query.order_by(Organization.created_at.desc()).limit(5).all()

    return render_template(
        "administration/index.html",
        org=org,
        total_orgs=total_orgs,
        total_users=total_users,
        total_requirements=total_requirements,
        total_audit_logs=total_audit_logs,
        recent_logs=recent_logs,
        orgs=orgs,
    )


@admin_bp.route("/organizations")
@login_required
@super_admin_required
def organizations():
    org = get_active_organization()
    all_orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    return render_template("administration/organizations.html", org=org, organizations=all_orgs)


@admin_bp.route("/organizations/<int:org_id>/toggle", methods=["POST"])
@login_required
@super_admin_required
def toggle_organization(org_id):
    target_org = Organization.query.get_or_404(org_id)
    target_org.is_active = not target_org.is_active
    db.session.commit()
    AuditService.log("ADMIN_TOGGLE_ORGANIZATION", "Organization", target_org.id, {"is_active": target_org.is_active})
    flash(f"Organization '{target_org.name}' status set to {'Active' if target_org.is_active else 'Inactive'}.", "info")
    return redirect(url_for("administration.organizations"))


@admin_bp.route("/regulatory-content")
@login_required
@super_admin_required
def regulatory_content():
    org = get_active_organization()
    domains = RegulatoryDomain.query.order_by(RegulatoryDomain.display_order).all()
    requirements = RegulatoryRequirement.query.order_by(RegulatoryRequirement.domain_id, RegulatoryRequirement.code).all()
    return render_template("administration/regulatory_content.html", org=org, domains=domains, requirements=requirements)


@admin_bp.route("/scoring-config", methods=["GET", "POST"])
@login_required
@super_admin_required
def scoring_config():
    org = get_active_organization()
    policy = ScoringPolicy.query.first()
    version = ScoringPolicyVersion.query.filter_by(is_active=True).first()

    if request.method == "POST":
        dp_w = float(request.form.get("weight_dp", 0.35))
        tax_w = float(request.form.get("weight_tax", 0.35))
        labour_w = float(request.form.get("weight_labour", 0.30))

        total_w = round(dp_w + tax_w + labour_w, 4)
        if total_w != 1.0:
            flash(f"Error: The sum of domain weights must equal exactly 1.0 (Current sum: {total_w}).", "danger")
            return render_template("administration/scoring_config.html", org=org, policy=policy, version=version)

        new_weights = {"DATA_PROTECTION": dp_w, "TAX": tax_w, "LABOUR": labour_w}
        version.domain_weights = new_weights
        db.session.commit()

        AuditService.log("UPDATE_SCORING_WEIGHTS", "ScoringPolicyVersion", version.id, new_weights)
        flash("Scoring weights successfully updated and saved.", "success")
        return redirect(url_for("administration.scoring_config"))

    return render_template("administration/scoring_config.html", org=org, policy=policy, version=version)


@admin_bp.route("/audit-logs")
@login_required
@super_admin_required
def audit_logs():
    org = get_active_organization()
    action_filter = request.args.get("action")
    entity_filter = request.args.get("entity")

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)

    logs = query.order_by(AuditLog.created_at.desc()).limit(100).all()

    return render_template(
        "administration/audit_logs.html",
        org=org,
        logs=logs,
        action_filter=action_filter,
        entity_filter=entity_filter,
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@super_admin_required
def settings():
    org = get_active_organization()
    if request.method == "POST":
        app_name = request.form.get("app_name", "CRAS").strip()
        lockout_attempts = request.form.get("lockout_attempts", "5").strip()
        lockout_minutes = request.form.get("lockout_minutes", "15").strip()

        SystemSetting.set_value("APP_NAME", app_name, "Application branding title")
        SystemSetting.set_value("MAX_FAILED_LOGIN_ATTEMPTS", lockout_attempts, "Max login failures before lockout")
        SystemSetting.set_value("ACCOUNT_LOCKOUT_MINUTES", lockout_minutes, "Lockout duration in minutes")
        db.session.commit()

        AuditService.log("UPDATE_SYSTEM_SETTINGS", "SystemSetting", None, {"app_name": app_name})
        flash("System settings saved successfully.", "success")
        return redirect(url_for("administration.settings"))

    app_name = SystemSetting.get_value("APP_NAME", "CRAS")
    lockout_attempts = SystemSetting.get_value("MAX_FAILED_LOGIN_ATTEMPTS", "5")
    lockout_minutes = SystemSetting.get_value("ACCOUNT_LOCKOUT_MINUTES", "15")

    return render_template(
        "administration/settings.html",
        org=org,
        app_name=app_name,
        lockout_attempts=lockout_attempts,
        lockout_minutes=lockout_minutes,
    )


@admin_bp.route("/populate-demo-data", methods=["POST"])
@login_required
@super_admin_required
def populate_demo_data():
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    stats = populate_comprehensive_live_data(upload_folder=upload_folder)

    AuditService.log(
        "POPULATE_LIVE_DEMO_DATA",
        "System",
        None,
        {
            "organizations": stats["organizations"],
            "assessments": stats["assessments"],
            "gaps": stats["gaps"],
            "actions": stats["actions"],
            "calendar_events": stats["calendar_events"],
            "evidence_files": stats["evidence_files"],
        },
    )

    flash(
        f"Live demonstration data successfully populated! {stats['organizations']} Kenyan SMEs refreshed with {stats['assessments']} multi-quarter assessments, {stats['gaps']} compliance gaps, {stats['actions']} corrective actions, {stats['calendar_events']} calendar deadlines, and {stats['evidence_files']} evidence files.",
        "success",
    )
    next_url = request.form.get("next") or request.referrer or url_for("administration.settings")
    return redirect(next_url)


