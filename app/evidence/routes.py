import os
import uuid
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models.base import db, utcnow
from app.models.auth import Role
from app.models.assessment import ComplianceAssessment, AssessmentEvidence
from app.models.regulatory import RegulatoryRequirement
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization, roles_required

evidence_bp = Blueprint("evidence", __name__, url_prefix="/evidence")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "image/jpeg",
    "image/png",
}


@evidence_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        flash("Please select an organization.", "warning")
        return redirect(url_for("dashboard.index"))

    evidence_list = AssessmentEvidence.query.filter_by(organization_id=org.id).order_by(
        AssessmentEvidence.uploaded_at.desc()
    ).all()

    return render_template("evidence/index.html", org=org, evidence_list=evidence_list)


@evidence_bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    org = get_active_organization()
    if not org:
        flash("Please select an organization.", "warning")
        return redirect(url_for("dashboard.index"))

    assessment_id = request.form.get("assessment_id", type=int)
    requirement_id = request.form.get("requirement_id", type=int)
    description = request.form.get("description", "").strip()

    if not assessment_id or not requirement_id:
        flash("Assessment ID and Requirement ID are required for evidence upload.", "danger")
        return redirect(request.referrer or url_for("evidence.index"))

    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()
    requirement = RegulatoryRequirement.query.get_or_404(requirement_id)

    if "file" not in request.files:
        flash("No file was selected for upload.", "warning")
        return redirect(request.referrer or url_for("evidence.index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "warning")
        return redirect(request.referrer or url_for("evidence.index"))

    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""

    if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        flash(f"Invalid file type .{extension}. Allowed formats are: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}", "danger")
        return redirect(request.referrer or url_for("evidence.index"))

    # Generate unique stored filename
    stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    full_path = upload_dir / stored_filename

    # Save file
    file.save(str(full_path))
    file_size = full_path.stat().st_size
    mime_type = file.mimetype or "application/octet-stream"

    evidence = AssessmentEvidence(
        organization_id=org.id,
        assessment_id=assessment.id,
        requirement_id=requirement.id,
        uploaded_by_id=current_user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size=file_size,
        mime_type=mime_type,
        file_path=str(full_path),
        description=description or f"Evidence for {requirement.code}",
        verification_status=AssessmentEvidence.STATUS_PENDING,
        uploaded_at=utcnow(),
    )
    db.session.add(evidence)
    db.session.commit()

    AuditService.log(
        "UPLOAD_EVIDENCE",
        "AssessmentEvidence",
        evidence.id,
        {"filename": original_filename, "size": file_size, "req_code": requirement.code},
        organization_id=org.id,
    )

    flash(f"Evidence '{original_filename}' uploaded successfully for obligation {requirement.code}.", "success")
    return redirect(request.referrer or url_for("evidence.index"))


@evidence_bp.route("/<int:evidence_id>/download")
@login_required
def download_file(evidence_id):
    org = get_active_organization()
    evidence = AssessmentEvidence.query.filter_by(id=evidence_id, organization_id=org.id).first_or_404()

    file_path = Path(evidence.file_path)
    if not file_path.exists():
        flash("Requested evidence file could not be found on server.", "danger")
        return redirect(url_for("evidence.index"))

    AuditService.log("DOWNLOAD_EVIDENCE", "AssessmentEvidence", evidence.id, {"filename": evidence.original_filename}, organization_id=org.id)

    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=evidence.original_filename,
        mimetype=evidence.mime_type,
    )


@evidence_bp.route("/<int:evidence_id>/verify", methods=["POST"])
@login_required
@roles_required(Role.ORG_ADMIN, Role.COMPLIANCE_OFFICER)
def verify_evidence(evidence_id):
    org = get_active_organization()
    evidence = AssessmentEvidence.query.filter_by(id=evidence_id, organization_id=org.id).first_or_404()

    status = request.form.get("status")
    if status in [AssessmentEvidence.STATUS_VERIFIED, AssessmentEvidence.STATUS_REJECTED]:
        evidence.verification_status = status
        db.session.commit()
        AuditService.log("VERIFY_EVIDENCE", "AssessmentEvidence", evidence.id, {"status": status}, organization_id=org.id)
        flash(f"Evidence '{evidence.original_filename}' marked as {status}.", "success")

    return redirect(request.referrer or url_for("evidence.index"))
