import json
from flask import request
from flask_login import current_user
from app.models.base import db
from app.models.audit_and_notification import AuditLog


class AuditService:
    @staticmethod
    def log(
        action: str,
        entity_type: str,
        entity_id: str = None,
        details: dict = None,
        user_id: int = None,
        organization_id: int = None,
    ):
        """Records a structured audit event into the database."""
        try:
            actual_user_id = user_id
            if actual_user_id is None and current_user and current_user.is_authenticated:
                actual_user_id = current_user.id

            ip_address = None
            user_agent = None
            if request:
                ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
                if ip_address and "," in ip_address:
                    ip_address = ip_address.split(",")[0].strip()
                user_agent = request.user_agent.string if request.user_agent else None

            details_str = json.dumps(details) if isinstance(details, dict) else str(details or "")

            audit_entry = AuditLog(
                user_id=actual_user_id,
                organization_id=organization_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None,
                details=details_str,
                ip_address=ip_address,
                user_agent=user_agent[:250] if user_agent else None,
            )
            db.session.add(audit_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Avoid crashing request if audit logging fails
            print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")
