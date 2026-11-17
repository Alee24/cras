import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.base import db
from app.models.auth import Role, User
from app.models.organization import Organization
from app.models.regulatory import RegulatoryDomain, RegulatoryCategory, RegulatoryRequirement, ComplianceQuestion
from app.models.assessment import AssessmentResponse
from app.models.compliance_management import ComplianceGap
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
    domain_id = request.args.get("domain_id", type=int)
    category_id = request.args.get("category_id", type=int)
    search_query = request.args.get("q", "").strip()

    domains = RegulatoryDomain.query.order_by(RegulatoryDomain.display_order).all()
    categories = RegulatoryCategory.query.order_by(RegulatoryCategory.domain_id, RegulatoryCategory.display_order).all()

    query = RegulatoryRequirement.query
    if domain_id:
        query = query.filter_by(domain_id=domain_id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search_query:
        query = query.filter(
            db.or_(
                RegulatoryRequirement.title.ilike(f"%{search_query}%"),
                RegulatoryRequirement.code.ilike(f"%{search_query}%"),
                RegulatoryRequirement.legal_reference.ilike(f"%{search_query}%"),
                RegulatoryRequirement.plain_description.ilike(f"%{search_query}%"),
            )
        )

    requirements = query.order_by(RegulatoryRequirement.domain_id, RegulatoryRequirement.code).all()

    total_requirements = RegulatoryRequirement.query.count()
    active_count = RegulatoryRequirement.query.filter_by(is_active=True).count()
    verified_count = RegulatoryRequirement.query.filter_by(verification_status=RegulatoryRequirement.VERIFIED).count()
    review_count = RegulatoryRequirement.query.filter_by(verification_status=RegulatoryRequirement.REQUIRES_LEGAL_REVIEW).count()

    return render_template(
        "administration/regulatory_content.html",
        org=org,
        domains=domains,
        categories=categories,
        requirements=requirements,
        total_requirements=total_requirements,
        active_count=active_count,
        verified_count=verified_count,
        review_count=review_count,
        selected_domain_id=domain_id,
        selected_category_id=category_id,
        search_query=search_query,
    )


@admin_bp.route("/regulatory-content/new", methods=["POST"])
@login_required
@super_admin_required
def create_requirement():
    code = request.form.get("code", "").strip().upper()
    title = request.form.get("title", "").strip()
    domain_id = request.form.get("domain_id", type=int)
    category_id = request.form.get("category_id", type=int)
    plain_description = request.form.get("plain_description", "").strip()
    legal_reference = request.form.get("legal_reference", "").strip()
    applicability_rule = request.form.get("applicability_rule", "All registered SMEs").strip()
    required_evidence_desc = request.form.get("required_evidence_desc", "").strip()
    risk_weight = float(request.form.get("risk_weight", 1.0))
    potential_consequence = request.form.get("potential_consequence", "").strip()
    recommended_corrective_action = request.form.get("recommended_corrective_action", "").strip()
    verification_status = request.form.get("verification_status", RegulatoryRequirement.VERIFIED)
    question_text = request.form.get("question_text", "").strip()
    question_help = request.form.get("question_help", "").strip()

    if not code or not title or not domain_id or not category_id:
        flash("Please provide Code, Title, Regulatory Domain, and Category.", "danger")
        return redirect(url_for("administration.regulatory_content"))

    existing = RegulatoryRequirement.query.filter_by(code=code).first()
    if existing:
        flash(f"A regulatory requirement with code '{code}' already exists.", "danger")
        return redirect(url_for("administration.regulatory_content"))

    req = RegulatoryRequirement(
        domain_id=domain_id,
        category_id=category_id,
        code=code,
        title=title,
        plain_description=plain_description,
        legal_reference=legal_reference,
        applicability_rule=applicability_rule,
        required_evidence_desc=required_evidence_desc,
        risk_weight=risk_weight,
        potential_consequence=potential_consequence,
        recommended_corrective_action=recommended_corrective_action,
        verification_status=verification_status,
        is_active=True,
    )
    db.session.add(req)
    db.session.flush()

    if question_text:
        q = ComplianceQuestion(
            requirement_id=req.id,
            question_text=question_text,
            help_text=question_help,
            display_order=1,
        )
        db.session.add(q)

    db.session.commit()
    AuditService.log("CREATE_REGULATORY_REQUIREMENT", "RegulatoryRequirement", req.id, {
        "code": req.code, "title": req.title, "domain_id": domain_id, "risk_weight": risk_weight
    })
    flash(f"Regulatory requirement '{req.code} - {req.title}' created successfully.", "success")
    return redirect(url_for("administration.regulatory_content"))


@admin_bp.route("/regulatory-content/<int:req_id>/edit", methods=["POST"])
@login_required
@super_admin_required
def edit_requirement(req_id):
    req = RegulatoryRequirement.query.get_or_404(req_id)

    code = request.form.get("code", "").strip().upper()
    title = request.form.get("title", "").strip()
    domain_id = request.form.get("domain_id", type=int)
    category_id = request.form.get("category_id", type=int)
    plain_description = request.form.get("plain_description", "").strip()
    legal_reference = request.form.get("legal_reference", "").strip()
    applicability_rule = request.form.get("applicability_rule", "").strip()
    required_evidence_desc = request.form.get("required_evidence_desc", "").strip()
    risk_weight = float(request.form.get("risk_weight", req.risk_weight))
    potential_consequence = request.form.get("potential_consequence", "").strip()
    recommended_corrective_action = request.form.get("recommended_corrective_action", "").strip()
    verification_status = request.form.get("verification_status", req.verification_status)
    is_active = request.form.get("is_active") == "1"

    if code and code != req.code:
        dup = RegulatoryRequirement.query.filter_by(code=code).first()
        if dup and dup.id != req.id:
            flash(f"Code '{code}' is already assigned to another requirement.", "danger")
            return redirect(url_for("administration.regulatory_content"))
        req.code = code

    if title:
        req.title = title
    if domain_id:
        req.domain_id = domain_id
    if category_id:
        req.category_id = category_id
    req.plain_description = plain_description
    req.legal_reference = legal_reference
    req.applicability_rule = applicability_rule
    req.required_evidence_desc = required_evidence_desc
    req.risk_weight = risk_weight
    req.potential_consequence = potential_consequence
    req.recommended_corrective_action = recommended_corrective_action
    req.verification_status = verification_status
    req.is_active = is_active

    question_text = request.form.get("question_text", "").strip()
    question_help = request.form.get("question_help", "").strip()
    question_id = request.form.get("question_id", type=int)

    if question_id:
        question = ComplianceQuestion.query.get(question_id)
        if question and question.requirement_id == req.id:
            if question_text:
                question.question_text = question_text
            question.help_text = question_help
    elif question_text:
        first_q = ComplianceQuestion.query.filter_by(requirement_id=req.id).first()
        if first_q:
            first_q.question_text = question_text
            first_q.help_text = question_help
        else:
            new_q = ComplianceQuestion(
                requirement_id=req.id,
                question_text=question_text,
                help_text=question_help,
                display_order=1
            )
            db.session.add(new_q)

    db.session.commit()
    AuditService.log("UPDATE_REGULATORY_REQUIREMENT", "RegulatoryRequirement", req.id, {
        "code": req.code, "title": req.title, "risk_weight": req.risk_weight, "is_active": req.is_active
    })
    flash(f"Regulatory requirement '{req.code}' updated successfully.", "success")
    return redirect(url_for("administration.regulatory_content"))


@admin_bp.route("/regulatory-content/<int:req_id>/toggle", methods=["POST"])
@login_required
@super_admin_required
def toggle_requirement(req_id):
    req = RegulatoryRequirement.query.get_or_404(req_id)
    req.is_active = not req.is_active
    db.session.commit()
    AuditService.log("TOGGLE_REGULATORY_REQUIREMENT", "RegulatoryRequirement", req.id, {"is_active": req.is_active})
    status_label = "activated" if req.is_active else "deactivated"
    flash(f"Requirement '{req.code}' has been {status_label}.", "info")
    return redirect(url_for("administration.regulatory_content"))


@admin_bp.route("/regulatory-content/<int:req_id>/delete", methods=["POST"])
@login_required
@super_admin_required
def delete_requirement(req_id):
    req = RegulatoryRequirement.query.get_or_404(req_id)
    has_responses = AssessmentResponse.query.filter_by(requirement_id=req.id).first() is not None
    has_gaps = ComplianceGap.query.filter_by(requirement_id=req.id).first() is not None

    if has_responses or has_gaps:
        req.is_active = False
        db.session.commit()
        AuditService.log("DEACTIVATE_REGULATORY_REQUIREMENT", "RegulatoryRequirement", req.id, {
            "reason": "Referenced in historical assessments/gaps; soft deactivated"
        })
        flash(f"Requirement '{req.code}' is referenced in assessment history; deactivated to maintain historical audit integrity.", "warning")
    else:
        req_code = req.code
        db.session.delete(req)
        db.session.commit()
        AuditService.log("DELETE_REGULATORY_REQUIREMENT", "RegulatoryRequirement", req_id, {"code": req_code})
        flash(f"Regulatory requirement '{req_code}' permanently deleted.", "success")

    return redirect(url_for("administration.regulatory_content"))


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


