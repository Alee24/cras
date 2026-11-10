from app.models.base import db, utcnow


class ComplianceAssessment(db.Model):
    __tablename__ = "compliance_assessments"

    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_COMPLETED = "COMPLETED"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    scoring_policy_version_id = db.Column(db.Integer, db.ForeignKey("scoring_policy_versions.id", ondelete="RESTRICT"), nullable=True)

    title = db.Column(db.String(200), nullable=False)
    assessment_period = db.Column(db.String(80), nullable=False, default="2026 Q1") # e.g. "2026 Q1", "Annual 2026"
    assessment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default=STATUS_DRAFT, nullable=False, index=True)

    # Scores
    overall_score = db.Column(db.Float, nullable=True) # 0.0 to 100.0
    risk_classification = db.Column(db.String(30), nullable=True) # HIGH_RISK, MODERATE_RISK, COMPLIANT

    # Counts
    total_obligations = db.Column(db.Integer, default=0, nullable=False)
    compliant_count = db.Column(db.Integer, default=0, nullable=False)
    partially_compliant_count = db.Column(db.Integer, default=0, nullable=False)
    non_compliant_count = db.Column(db.Integer, default=0, nullable=False)
    not_applicable_count = db.Column(db.Integer, default=0, nullable=False)
    not_assessed_count = db.Column(db.Integer, default=0, nullable=False)

    notes = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy="joined")
    scoring_policy_version = db.relationship("ScoringPolicyVersion", lazy="joined")
    responses = db.relationship("AssessmentResponse", backref="assessment", cascade="all, delete-orphan", lazy="selectin")
    domain_scores = db.relationship("AssessmentDomainScore", backref="assessment", cascade="all, delete-orphan", lazy="selectin")
    evidence_files = db.relationship("AssessmentEvidence", backref="assessment", cascade="all, delete-orphan", lazy="selectin")
    gaps = db.relationship("ComplianceGap", backref="assessment", cascade="all, delete-orphan", lazy="dynamic")
    actions = db.relationship("CorrectiveAction", backref="assessment", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def is_editable(self) -> bool:
        return self.status == self.STATUS_DRAFT

    def __repr__(self):
        return f"<ComplianceAssessment id={self.id} org={self.organization_id} score={self.overall_score}>"


class AssessmentResponse(db.Model):
    __tablename__ = "assessment_responses"

    RESPONSE_COMPLIANT = "COMPLIANT"
    RESPONSE_PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    RESPONSE_NON_COMPLIANT = "NON_COMPLIANT"
    RESPONSE_NOT_APPLICABLE = "NOT_APPLICABLE"
    RESPONSE_NOT_ASSESSED = "NOT_ASSESSED"

    VALID_RESPONSES = [
        RESPONSE_COMPLIANT,
        RESPONSE_PARTIALLY_COMPLIANT,
        RESPONSE_NON_COMPLIANT,
        RESPONSE_NOT_APPLICABLE,
        RESPONSE_NOT_ASSESSED,
    ]

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("compliance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey("regulatory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    response_value = db.Column(db.String(30), default=RESPONSE_NOT_ASSESSED, nullable=False)
    response_score = db.Column(db.Float, nullable=True) # Normalized score (1.0, 0.5, 0.0, or None if N/A)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    requirement = db.relationship("RegulatoryRequirement", lazy="joined")
    updated_by = db.relationship("User", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("assessment_id", "requirement_id", name="uq_assessment_req"),
    )

    def __repr__(self):
        return f"<AssessmentResponse req={self.requirement_id} val={self.response_value}>"


class AssessmentDomainScore(db.Model):
    __tablename__ = "assessment_domain_scores"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("compliance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("regulatory_domains.id", ondelete="CASCADE"), nullable=False, index=True)

    raw_score = db.Column(db.Float, nullable=False) # e.g. sum of (risk_weight * response_score)
    normalized_score = db.Column(db.Float, nullable=False) # 0.0 to 1.0 (Ci)
    domain_weight = db.Column(db.Float, nullable=False) # Wi (e.g. 0.35)
    weighted_score = db.Column(db.Float, nullable=False) # Wi * Ci * 100
    classification = db.Column(db.String(30), nullable=False) # HIGH_RISK, MODERATE_RISK, COMPLIANT

    applicable_obligations_count = db.Column(db.Integer, default=0, nullable=False)
    compliant_count = db.Column(db.Integer, default=0, nullable=False)
    partially_compliant_count = db.Column(db.Integer, default=0, nullable=False)
    non_compliant_count = db.Column(db.Integer, default=0, nullable=False)
    not_applicable_count = db.Column(db.Integer, default=0, nullable=False)

    domain = db.relationship("RegulatoryDomain", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("assessment_id", "domain_id", name="uq_assessment_domain"),
    )

    def __repr__(self):
        return f"<AssessmentDomainScore domain={self.domain_id} score={self.normalized_score}>"


class AssessmentEvidence(db.Model):
    __tablename__ = "assessment_evidence"

    STATUS_PENDING = "PENDING"
    STATUS_VERIFIED = "VERIFIED"
    STATUS_REJECTED = "REJECTED"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("compliance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey("regulatory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    file_size = db.Column(db.Integer, nullable=False) # bytes
    mime_type = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    verification_status = db.Column(db.String(30), default=STATUS_PENDING, nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    requirement = db.relationship("RegulatoryRequirement", lazy="joined")
    uploaded_by = db.relationship("User", lazy="joined")
    organization = db.relationship("Organization", lazy="joined")

    def __repr__(self):
        return f"<AssessmentEvidence {self.original_filename} req={self.requirement_id}>"

