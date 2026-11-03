from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.base import db, utcnow
from app.models.auth import Role
from app.models.assessment import ComplianceAssessment, AssessmentResponse, AssessmentDomainScore, AssessmentEvidence
from app.models.regulatory import RegulatoryDomain, RegulatoryRequirement
from app.models.scoring import ScoringPolicy, ScoringPolicyVersion
from app.services.scoring_service import ScoringEngine, ScoringValidationError
from app.services.compliance_gap_service import ComplianceGapService
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization, roles_required

assessments_bp = Blueprint("assessments", __name__, url_prefix="/assessments")


@assessments_bp.route("/")
@login_required
def list_assessments():
    org = get_active_organization()
    if not org:
        flash("Please select or create an organization first.", "warning")
        return redirect(url_for("dashboard.index"))

    assessments = ComplianceAssessment.query.filter_by(organization_id=org.id).order_by(
        ComplianceAssessment.created_at.desc()
    ).all()

    return render_template("assessments/list.html", org=org, assessments=assessments)


@assessments_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required(Role.ORG_ADMIN, Role.COMPLIANCE_OFFICER)
def create_assessment():
    org = get_active_organization()
    if not org:
        flash("Please select an organization first.", "warning")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        period = request.form.get("assessment_period", "").strip()
        assessment_date_str = request.form.get("assessment_date")
        notes = request.form.get("notes", "").strip()

        if not title or not period or not assessment_date_str:
            flash("Please provide an assessment title, period, and date.", "danger")
            return render_template("assessments/create.html", org=org)

        try:
            a_date = date.fromisoformat(assessment_date_str)
        except ValueError:
            a_date = date.today()

        # Get active scoring policy version
        policy_version = ScoringPolicyVersion.query.filter_by(is_active=True).first()
        if not policy_version:
            # Seed scoring policy if missing
            from app.services.seed_data import seed_scoring_policy
            _, policy_version = seed_scoring_policy()

        # Create assessment
        assessment = ComplianceAssessment(
            organization_id=org.id,
            created_by_id=current_user.id,
            scoring_policy_version_id=policy_version.id,
            title=title,
            assessment_period=period,
            assessment_date=a_date,
            status=ComplianceAssessment.STATUS_DRAFT,
            notes=notes,
        )
        db.session.add(assessment)
        db.session.flush()

        # Initialize responses for all active requirements
        requirements = RegulatoryRequirement.query.filter_by(is_active=True).order_by(
            RegulatoryRequirement.domain_id, RegulatoryRequirement.display_order
        ).all()

        for req in requirements:
            resp = AssessmentResponse(
                assessment_id=assessment.id,
                requirement_id=req.id,
                response_value=AssessmentResponse.RESPONSE_NOT_ASSESSED,
                updated_by_id=current_user.id,
            )
            db.session.add(resp)

        assessment.total_obligations = len(requirements)
        db.session.commit()

        AuditService.log("CREATE_ASSESSMENT", "ComplianceAssessment", assessment.id, {"title": title, "period": period}, organization_id=org.id)

        flash(f"Assessment '{title}' created successfully. You can now conduct the compliance review.", "success")
        return redirect(url_for("assessments.conduct_assessment", assessment_id=assessment.id))

    return render_template("assessments/create.html", org=org)


@assessments_bp.route("/<int:assessment_id>")
@login_required
def view_assessment(assessment_id):
    org = get_active_organization()
    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()
    domain_scores = AssessmentDomainScore.query.filter_by(assessment_id=assessment.id).all()
    evidence_files = AssessmentEvidence.query.filter_by(assessment_id=assessment.id).all()

    return render_template(
        "assessments/view.html",
        org=org,
        assessment=assessment,
        domain_scores=domain_scores,
        evidence_files=evidence_files,
    )


@assessments_bp.route("/<int:assessment_id>/conduct", methods=["GET", "POST"])
@login_required
@roles_required(Role.ORG_ADMIN, Role.COMPLIANCE_OFFICER, Role.FINANCE_MANAGER, Role.HR_MANAGER)
def conduct_assessment(assessment_id):
    org = get_active_organization()
    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()

    if not assessment.is_editable:
        flash("This assessment has already been finalized and cannot be modified. Completed records are immutable.", "info")
        return redirect(url_for("assessments.view_assessment", assessment_id=assessment.id))

    domains = RegulatoryDomain.query.filter_by(is_active=True).order_by(RegulatoryDomain.display_order).all()
    responses = {r.requirement_id: r for r in assessment.responses}

    # Handle form submission
    if request.method == "POST":
        action = request.form.get("action", "save_draft")

        # Update responses from form data
        all_reqs = RegulatoryRequirement.query.filter_by(is_active=True).all()
        for req in all_reqs:
            resp_val = request.form.get(f"response_{req.id}")
            notes_val = request.form.get(f"notes_{req.id}", "").strip()

            resp = responses.get(req.id)
            if resp and resp_val:
                resp.response_value = resp_val
                resp.notes = notes_val
                resp.updated_by_id = current_user.id
                resp.updated_at = utcnow()

        db.session.commit()

        if action == "finalize":
            policy_version = assessment.scoring_policy_version or ScoringPolicyVersion.query.filter_by(is_active=True).first()
            try:
                # Calculate deterministic scores
                ScoringEngine.apply_and_persist_scores(assessment, policy_version)

                # Mark completed
                assessment.status = ComplianceAssessment.STATUS_COMPLETED
                assessment.completed_at = utcnow()
                db.session.commit()

                # Sync compliance gaps automatically
                gaps_count = ComplianceGapService.sync_gaps_for_assessment(assessment)

                AuditService.log(
                    "SUBMIT_ASSESSMENT",
                    "ComplianceAssessment",
                    assessment.id,
                    {
                        "overall_score": assessment.overall_score,
                        "risk_classification": assessment.risk_classification,
                        "gaps_generated": gaps_count,
                    },
                    organization_id=org.id,
                )

                flash(
                    f"Compliance Assessment finalized! Overall Score: {assessment.overall_score:.2f}% "
                    f"({assessment.risk_classification.replace('_', ' ')}). "
                    f"{gaps_count} compliance gap(s) identified for action.",
                    "success"
                )
                return redirect(url_for("assessments.view_assessment", assessment_id=assessment.id))

            except ScoringValidationError as err:
                db.session.rollback()
                flash(f"Submission Incomplete: {str(err)}", "danger")
                return redirect(url_for("assessments.conduct_assessment", assessment_id=assessment.id))

        else:
            AuditService.log("SAVE_ASSESSMENT_DRAFT", "ComplianceAssessment", assessment.id, {}, organization_id=org.id)
            flash("Assessment draft saved successfully. You can continue later.", "info")
            return redirect(url_for("assessments.conduct_assessment", assessment_id=assessment.id))

    return render_template(
        "assessments/conduct.html",
        org=org,
        assessment=assessment,
        domains=domains,
        responses=responses,
    )

