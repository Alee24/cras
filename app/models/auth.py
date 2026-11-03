from datetime import datetime, timezone, timedelta
from flask_login import UserMixin
import bcrypt
from app.models.base import db, utcnow


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Role(db.Model):
    __tablename__ = "roles"

    SUPER_ADMIN = "SUPER_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    HR_MANAGER = "HR_MANAGER"
    AUDITOR = "AUDITOR"

    ALL_ROLES = [SUPER_ADMIN, ORG_ADMIN, COMPLIANCE_OFFICER, FINANCE_MANAGER, HR_MANAGER, AUDITOR]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    permissions = db.relationship("Permission", secondary="role_permissions", backref="roles", lazy="selectin")

    def __repr__(self):
        return f"<Role {self.name}>"


role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(40), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=True, nullable=False) # For demo/initial SME onboarding
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    user_roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    organization_memberships = db.relationship("OrganizationUser", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    notifications = db.relationship("Notification", backref="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))
        except Exception:
            return False

    @property
    def is_locked(self) -> bool:
        if self.locked_until:
            target = self.locked_until
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return target > utcnow()
        return False

    def record_failed_login(self, max_attempts: int = 5, lock_minutes: int = 15) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = utcnow() + timedelta(minutes=lock_minutes)

    def record_successful_login(self) -> None:
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = utcnow()

    @property
    def is_super_admin(self) -> bool:
        return any(ur.role.name == Role.SUPER_ADMIN for ur in self.user_roles)

    def has_role(self, role_name: str, org_id: int = None) -> bool:
        if self.is_super_admin:
            return True
        if org_id is not None:
            for membership in self.organization_memberships:
                if membership.organization_id == org_id and membership.role.name == role_name:
                    return True
        return any(ur.role.name == role_name for ur in self.user_roles)

    def get_role_in_org(self, org_id: int):
        for membership in self.organization_memberships:
            if membership.organization_id == org_id:
                return membership.role.name
        if self.is_super_admin:
            return Role.SUPER_ADMIN
        return None

    def __repr__(self):
        return f"<User {self.email}>"


class UserRole(db.Model):
    __tablename__ = "user_roles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="user_roles")
    role = db.relationship("Role", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
