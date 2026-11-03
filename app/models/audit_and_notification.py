from app.models.base import db, utcnow


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(40), default="INFO", nullable=False) # DEADLINE, OVERDUE, GAP, ACTION, ASSESSMENT, SYSTEM
    link_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<Notification user={self.user_id} title={self.title} read={self.is_read}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)

    action = db.Column(db.String(100), nullable=False, index=True) # CREATE, UPDATE, DELETE, SUBMIT, LOGIN, LOGOUT, EXPORT
    entity_type = db.Column(db.String(80), nullable=False, index=True) # Assessment, User, Organization, Evidence, Action
    entity_id = db.Column(db.String(80), nullable=True)
    details = db.Column(db.Text, nullable=True) # JSON representation or audit note
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = db.relationship("User", lazy="joined")
    organization = db.relationship("Organization", lazy="joined")

    def __repr__(self):
        return f"<AuditLog action={self.action} entity={self.entity_type}:{self.entity_id}>"


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    @classmethod
    def get_value(cls, key: str, default: str = None) -> str:
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_value(cls, key: str, value: str, description: str = None) -> "SystemSetting":
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        else:
            setting.value = value
            if description:
                setting.description = description
        return setting

    def __repr__(self):
        return f"<SystemSetting {self.key}>"
