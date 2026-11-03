from app.models.base import db, utcnow


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    business_registration_number = db.Column(db.String(80), unique=True, nullable=False, index=True)
    kra_pin = db.Column(db.String(30), unique=True, nullable=False, index=True)
    industry_sector = db.Column(db.String(100), nullable=False, default="Services") # e.g. Finance, Healthcare, Retail, Technology, Manufacturing, Agriculture
    business_type = db.Column(db.String(80), nullable=False, default="Private Limited Company") # Sole Proprietorship, Partnership, Private Limited, etc.
    organization_size = db.Column(db.String(50), nullable=False, default="Small (10-49)") # Micro (1-9), Small (10-49), Medium (50-249)
    employee_count = db.Column(db.Integer, nullable=False, default=15)
    physical_address = db.Column(db.String(255), nullable=True)
    county = db.Column(db.String(80), nullable=False, default="Nairobi")
    contact_email = db.Column(db.String(180), nullable=False)
    phone_number = db.Column(db.String(40), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    registration_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    departments = db.relationship("Department", backref="organization", cascade="all, delete-orphan", lazy="selectin")
    memberships = db.relationship("OrganizationUser", back_populates="organization", cascade="all, delete-orphan", lazy="selectin")
    assessments = db.relationship("ComplianceAssessment", backref="organization", cascade="all, delete-orphan", lazy="dynamic")
    compliance_gaps = db.relationship("ComplianceGap", backref="organization", cascade="all, delete-orphan", lazy="dynamic")
    corrective_actions = db.relationship("CorrectiveAction", backref="organization", cascade="all, delete-orphan", lazy="dynamic")
    deadlines = db.relationship("ComplianceDeadline", backref="organization", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<Organization {self.name} ({self.kra_pin})>"


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("organization_id", "name", name="uq_org_dept_name"),
    )

    def __repr__(self):
        return f"<Department {self.name}>"


class OrganizationUser(db.Model):
    __tablename__ = "organization_users"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    organization = db.relationship("Organization", back_populates="memberships")
    user = db.relationship("User", back_populates="organization_memberships")
    role = db.relationship("Role", lazy="joined")
    department = db.relationship("Department", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    def __repr__(self):
        return f"<OrganizationUser org={self.organization_id} user={self.user_id} role={self.role_id}>"
