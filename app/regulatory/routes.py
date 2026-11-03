from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.regulatory import RegulatoryDomain, RegulatoryCategory, RegulatoryRequirement
from app.utils.decorators import get_active_organization

regulatory_bp = Blueprint("regulatory", __name__, url_prefix="/regulatory")


@regulatory_bp.route("/")
@login_required
def framework():
    org = get_active_organization()
    domains = RegulatoryDomain.query.filter_by(is_active=True).order_by(RegulatoryDomain.display_order).all()
    selected_domain_code = request.args.get("domain", "DATA_PROTECTION")

    selected_domain = RegulatoryDomain.query.filter_by(code=selected_domain_code).first()
    if not selected_domain and domains:
        selected_domain = domains[0]

    categories = []
    if selected_domain:
        categories = RegulatoryCategory.query.filter_by(domain_id=selected_domain.id).order_by(
            RegulatoryCategory.display_order
        ).all()

    total_requirements = RegulatoryRequirement.query.filter_by(is_active=True).count()

    return render_template(
        "regulatory/framework.html",
        org=org,
        domains=domains,
        selected_domain=selected_domain,
        categories=categories,
        total_requirements=total_requirements,
    )


@regulatory_bp.route("/requirement/<int:req_id>")
@login_required
def requirement_detail(req_id):
    org = get_active_organization()
    req = RegulatoryRequirement.query.get_or_404(req_id)
    return render_template("regulatory/detail.html", org=org, req=req)
