from flask import Blueprint, render_template, send_file, Response, redirect, url_for, flash
from flask_login import login_required
from app.models.assessment import ComplianceAssessment
from app.services.reporting_service import ReportingService
from app.services.audit_service import AuditService
from app.utils.decorators import get_active_organization

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def index():
    org = get_active_organization()
    if not org:
        flash("Please select an organization.", "warning")
        return redirect(url_for("dashboard.index"))

    assessments = ComplianceAssessment.query.filter_by(organization_id=org.id).order_by(
        ComplianceAssessment.assessment_date.desc(), ComplianceAssessment.id.desc()
    ).all()

    return render_template("reports/index.html", org=org, assessments=assessments)


@reports_bp.route("/assessment/<int:assessment_id>/pdf")
@login_required
def download_pdf(assessment_id):
    org = get_active_organization()
    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()

    pdf_buffer = ReportingService.generate_assessment_pdf(assessment)
    filename = f"CRAS_Compliance_Report_{org.name.replace(' ', '_')}_{assessment.assessment_period.replace(' ', '_')}.pdf"

    AuditService.log("EXPORT_PDF_REPORT", "ComplianceAssessment", assessment.id, {"filename": filename}, organization_id=org.id)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


@reports_bp.route("/assessment/<int:assessment_id>/print")
@login_required
def print_report(assessment_id):
    org = get_active_organization()
    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()
    domain_scores = assessment.domain_scores
    gaps = assessment.gaps.all()
    actions = assessment.actions.all()

    return render_template(
        "reports/print.html",
        org=org,
        assessment=assessment,
        domain_scores=domain_scores,
        gaps=gaps,
        actions=actions,
    )


@reports_bp.route("/assessment/<int:assessment_id>/csv")
@login_required
def download_assessment_csv(assessment_id):
    org = get_active_organization()
    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()

    csv_data = ReportingService.generate_assessment_csv(assessment)
    filename = f"CRAS_Assessment_{assessment.assessment_period.replace(' ', '_')}.csv"

    AuditService.log("EXPORT_CSV_ASSESSMENT", "ComplianceAssessment", assessment.id, {"filename": filename}, organization_id=org.id)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/assessment/<int:assessment_id>/excel")
@login_required
def download_assessment_excel(assessment_id):
    org = get_active_organization()
    assessment = ComplianceAssessment.query.filter_by(id=assessment_id, organization_id=org.id).first_or_404()

    stream = ReportingService.generate_excel_export(assessment)
    filename = f"CRAS_Compliance_Assessment_{assessment.assessment_period.replace(' ', '_')}.xlsx"

    AuditService.log("EXPORT_EXCEL_ASSESSMENT", "ComplianceAssessment", assessment.id, {"filename": filename}, organization_id=org.id)

    return send_file(
        stream,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@reports_bp.route("/gaps/csv")
@login_required
def download_gaps_csv():
    org = get_active_organization()
    csv_data = ReportingService.generate_gaps_csv(org.id)
    filename = f"CRAS_Compliance_Gaps_{org.name.replace(' ', '_')}.csv"

    AuditService.log("EXPORT_CSV_GAPS", "ComplianceGap", None, {"filename": filename}, organization_id=org.id)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
