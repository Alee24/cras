from app.models.base import db, utcnow


class ComplianceGap(db.Model):
    __tablename__ = "compliance_gaps"

    STATUS_OPEN = "OPEN"
    STATUS_ASSIGNED = "ASSIGNED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_CLOSED = "CLOSED"

    SEVERITY_CRITICAL = "CRITICAL"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_LOW = "LOW"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("compliance_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey("regulatory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("regulatory_domains.id", ondelete="CASCADE"), nullable=False, index=True)

    gap_title = db.Column(db.String(255), nullable=False)
    gap_description = db.Column(db.Text, nullable=False)
    legal_reference = db.Column(db.String(255), nullable=False)
    potential_consequence = db.Column(db.Text, nullable=True)
    recommended_action = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), default=SEVERITY_HIGH, nullable=False)
    status = db.Column(db.String(30), default=STATUS_OPEN, nullable=False, index=True)

    identified_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    requirement = db.relationship("RegulatoryRequirement", lazy="joined")
    domain = db.relationship("RegulatoryDomain", lazy="joined")
    actions = db.relationship("CorrectiveAction", backref="gap", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<ComplianceGap id={self.id} title={self.gap_title}>"


class CorrectiveAction(db.Model):
    __tablename__ = "corrective_actions"

    STATUS_OPEN = "OPEN"
    STATUS_ASSIGNED = "ASSIGNED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_PENDING_VERIFICATION = "PENDING_VERIFICATION"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_CLOSED = "CLOSED"

    PRIORITY_CRITICAL = "CRITICAL"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_LOW = "LOW"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    gap_id = db.Column(db.Integer, db.ForeignKey("compliance_gaps.id", ondelete="CASCADE"), nullable=True, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("compliance_assessments.id", ondelete="CASCADE"), nullable=True, index=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey("regulatory_requirements.id", ondelete="SET NULL"), nullable=True)

    title = db.Column(db.String(255), nullable=False)
    action_description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default=PRIORITY_HIGH, nullable=False)
    status = db.Column(db.String(30), default=STATUS_OPEN, nullable=False, index=True)

    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id], lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy="joined")
    requirement = db.relationship("RegulatoryRequirement", lazy="joined")

    def __repr__(self):
        return f"<CorrectiveAction id={self.id} title={self.title} status={self.status}>"


class ComplianceDeadline(db.Model):
    __tablename__ = "compliance_deadlines"

    STATUS_PENDING = "PENDING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_OVERDUE = "OVERDUE"

    RECURRENCE_MONTHLY = "MONTHLY"
    RECURRENCE_QUARTERLY = "QUARTERLY"
    RECURRENCE_ANNUAL = "ANNUAL"
    RECURRENCE_NONE = "NONE"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("regulatory_domains.id", ondelete="SET NULL"), nullable=True)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    legal_reference = db.Column(db.String(255), nullable=True)
    statutory_rule = db.Column(db.String(255), nullable=True) # e.g. "9th of following month"
    
    deadline_type = db.Column(db.String(30), default="STATUTORY_RECURRING", nullable=False)
    recurrence = db.Column(db.String(30), default=RECURRENCE_MONTHLY, nullable=False)
    current_due_date = db.Column(db.Date, nullable=False, index=True)
    reminder_days_before = db.Column(db.Integer, default=5, nullable=False)

    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    domain = db.relationship("RegulatoryDomain", lazy="joined")

    def __repr__(self):
        return f"<ComplianceDeadline title={self.title} due={self.current_due_date}>"

