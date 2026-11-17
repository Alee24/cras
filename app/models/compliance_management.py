import calendar as calendar_mod
from datetime import date
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
    last_completed_due_date = db.Column(db.Date, nullable=True)
    completed_cycle_until = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    domain = db.relationship("RegulatoryDomain", lazy="joined")

    def advance_to_next_cycle(self, today=None):
        """Advances current_due_date to the next recurrence cycle upon completion while setting
        completed_cycle_until so that the compliance status remains COMPLETED until the current cycle period concludes.
        """
        if not today:
            today = date.today()

        self.last_completed_due_date = self.current_due_date
        self.completed_at = utcnow()
        self.status = self.STATUS_COMPLETED

        current_year = self.current_due_date.year
        current_month = self.current_due_date.month
        current_day = self.current_due_date.day

        if self.recurrence == self.RECURRENCE_ANNUAL:
            next_year = current_year + 1
            try:
                self.current_due_date = date(next_year, current_month, current_day)
            except ValueError:
                self.current_due_date = date(next_year, current_month, 28)
            # Status remains COMPLETED till the end of the completed year (Dec 31)
            self.completed_cycle_until = date(current_year, 12, 31)

        elif self.recurrence == self.RECURRENCE_MONTHLY:
            if current_month == 12:
                next_year = current_year + 1
                next_month = 1
            else:
                next_year = current_year
                next_month = current_month + 1

            max_day = calendar_mod.monthrange(next_year, next_month)[1]
            target_day = min(current_day, max_day)
            self.current_due_date = date(next_year, next_month, target_day)

            # Status remains COMPLETED till the end of the completed month
            comp_month_max_day = calendar_mod.monthrange(current_year, current_month)[1]
            self.completed_cycle_until = date(current_year, current_month, comp_month_max_day)

        elif self.recurrence == self.RECURRENCE_QUARTERLY:
            new_month = current_month + 3
            if new_month > 12:
                next_year = current_year + 1
                next_month = new_month - 12
            else:
                next_year = current_year
                next_month = new_month

            max_day = calendar_mod.monthrange(next_year, next_month)[1]
            target_day = min(current_day, max_day)
            self.current_due_date = date(next_year, next_month, target_day)

            quarter = (current_month - 1) // 3 + 1
            q_end_month = quarter * 3
            q_end_day = calendar_mod.monthrange(current_year, q_end_month)[1]
            self.completed_cycle_until = date(current_year, q_end_month, q_end_day)

        else:
            self.completed_cycle_until = None

    def reopen_previous_cycle(self, today=None):
        """Restores deadline to the previous cycle if previously advanced upon completion."""
        if not today:
            today = date.today()

        if self.last_completed_due_date:
            self.current_due_date = self.last_completed_due_date
            self.last_completed_due_date = None

        self.completed_cycle_until = None
        self.completed_at = None

        if self.current_due_date < today:
            self.status = self.STATUS_OVERDUE
        else:
            self.status = self.STATUS_PENDING

    def refresh_status_for_date(self, today=None):
        """Refreshes status based on cycle expiry and current date."""
        if not today:
            today = date.today()

        if self.status == self.STATUS_COMPLETED:
            if self.completed_cycle_until and today > self.completed_cycle_until:
                # Cycle has concluded; reset status for the new period
                self.completed_cycle_until = None
                if today > self.current_due_date:
                    self.status = self.STATUS_OVERDUE
                else:
                    self.status = self.STATUS_PENDING
        elif self.status == self.STATUS_PENDING:
            if self.current_due_date < today:
                self.status = self.STATUS_OVERDUE
        elif self.status == self.STATUS_OVERDUE:
            if self.current_due_date >= today:
                self.status = self.STATUS_PENDING

    def __repr__(self):
        return f"<ComplianceDeadline title={self.title} due={self.current_due_date}>"

