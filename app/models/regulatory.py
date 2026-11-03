from app.models.base import db, utcnow


class RegulatoryDomain(db.Model):
    __tablename__ = "regulatory_domains"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True) # DATA_PROTECTION, TAX, LABOUR
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    legal_framework = db.Column(db.String(255), nullable=False) # e.g. "Data Protection Act 2019"
    icon = db.Column(db.String(50), default="fa-shield-halved")
    display_order = db.Column(db.Integer, default=1, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    categories = db.relationship("RegulatoryCategory", backref="domain", cascade="all, delete-orphan", order_by="RegulatoryCategory.display_order", lazy="selectin")
    requirements = db.relationship("RegulatoryRequirement", backref="domain", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<RegulatoryDomain {self.code}: {self.title}>"


class RegulatoryCategory(db.Model):
    __tablename__ = "regulatory_categories"

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("regulatory_domains.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    requirements = db.relationship("RegulatoryRequirement", backref="category", cascade="all, delete-orphan", order_by="RegulatoryRequirement.display_order", lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("domain_id", "code", name="uq_domain_cat_code"),
    )

    def __repr__(self):
        return f"<RegulatoryCategory {self.code}>"


class RegulatoryRequirement(db.Model):
    __tablename__ = "regulatory_requirements"

    VERIFIED = "VERIFIED"
    REQUIRES_LEGAL_REVIEW = "REQUIRES_LEGAL_REVIEW"

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("regulatory_domains.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("regulatory_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    plain_description = db.Column(db.Text, nullable=False)
    legal_reference = db.Column(db.String(255), nullable=False) # e.g. "Data Protection Act 2019, Section 18"
    applicability_rule = db.Column(db.String(255), nullable=True, default="All registered SMEs")
    required_evidence_desc = db.Column(db.Text, nullable=True)
    risk_weight = db.Column(db.Float, default=1.0, nullable=False) # 1.0 (Standard) to 3.0 (Critical)
    potential_consequence = db.Column(db.Text, nullable=True) # Statutory fines, prosecution, penalties
    recommended_corrective_action = db.Column(db.Text, nullable=True)
    effective_date = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    verification_status = db.Column(db.String(30), default=VERIFIED, nullable=False)
    display_order = db.Column(db.Integer, default=1, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    questions = db.relationship("ComplianceQuestion", backref="requirement", cascade="all, delete-orphan", order_by="ComplianceQuestion.display_order", lazy="selectin")

    def __repr__(self):
        return f"<RegulatoryRequirement {self.code}: {self.title}>"


class ComplianceQuestion(db.Model):
    __tablename__ = "compliance_questions"

    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey("regulatory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    help_text = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self):
        return f"<ComplianceQuestion {self.id} for req={self.requirement_id}>"
