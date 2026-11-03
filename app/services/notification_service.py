from app.models.base import db
from app.models.audit_and_notification import Notification
from app.models.auth import User, Role
from app.models.organization import OrganizationUser


class NotificationService:
    @staticmethod
    def notify_user(user_id: int, title: str, message: str, notification_type: str = "INFO", link_url: str = None, org_id: int = None):
        """Creates an in-app notification for a specific user."""
        try:
            notif = Notification(
                user_id=user_id,
                organization_id=org_id,
                title=title,
                message=message,
                notification_type=notification_type,
                link_url=link_url,
                is_read=False,
            )
            db.session.add(notif)
            db.session.commit()
            return notif
        except Exception as e:
            db.session.rollback()
            print(f"[NOTIFICATION ERROR] {e}")
            return None

    @staticmethod
    def notify_organization_role(org_id: int, role_name: str, title: str, message: str, notification_type: str = "INFO", link_url: str = None):
        """Notifies all members of an organization who have a specific role."""
        try:
            members = OrganizationUser.query.join(Role).filter(
                OrganizationUser.organization_id == org_id,
                Role.name == role_name,
            ).all()
            for m in members:
                NotificationService.notify_user(
                    user_id=m.user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    link_url=link_url,
                    org_id=org_id,
                )
        except Exception as e:
            print(f"[NOTIFICATION ORG ROLE ERROR] {e}")
