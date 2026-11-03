import os
from flask import Flask, redirect, url_for, session, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup

from app.config import config_by_name
from app.models.base import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, OrganizationUser
from app.models.audit_and_notification import Notification

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.assessments.routes import assessments_bp
    from app.compliance_gaps.routes import compliance_gaps_bp
    from app.corrective_actions.routes import corrective_actions_bp
    from app.calendar.routes import calendar_bp
    from app.evidence.routes import evidence_bp
    from app.analytics.routes import analytics_bp
    from app.reports.routes import reports_bp
    from app.organizations.routes import organizations_bp
    from app.users.routes import users_bp
    from app.regulatory.routes import regulatory_bp
    from app.notifications.routes import notifications_bp
    from app.administration.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(assessments_bp)
    app.register_blueprint(compliance_gaps_bp)
    app.register_blueprint(corrective_actions_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(regulatory_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)

    # Health Check Endpoint
    @app.route("/health")
    def health_check():
        try:
            # Check DB connection
            db.session.execute(db.select(1))
            return {"status": "healthy", "service": "CRAS", "database": "connected"}, 200
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}, 500

    # Root route redirect
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    # Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Global Context Processors
    @app.context_processor
    def inject_global_context():
        from app.utils.decorators import get_active_organization
        active_org = get_active_organization()
        user_orgs = []
        unread_count = 0
        current_role_name = "User"

        if current_user.is_authenticated:
            if current_user.is_super_admin:
                user_orgs = Organization.query.filter_by(is_active=True).all()
                current_role_name = "Super Admin"
            else:
                user_orgs = [m.organization for m in current_user.organization_memberships if m.organization.is_active]
                if active_org:
                    current_role_name = current_user.get_role_in_org(active_org.id) or "Member"

            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

        return {
            "current_org": active_org,
            "user_organizations": user_orgs,
            "unread_notifications_count": unread_count,
            "current_role_name": current_role_name,
        }

    # Custom Jinja Template Filters
    @app.template_filter("status_badge")
    def status_badge_filter(status):
        badges = {
            "COMPLETED": "bg-success",
            "RESOLVED": "bg-success",
            "CLOSED": "bg-secondary",
            "SUBMITTED": "bg-primary",
            "IN_PROGRESS": "bg-info text-dark",
            "ASSIGNED": "bg-warning text-dark",
            "OPEN": "bg-danger",
            "OVERDUE": "bg-danger",
            "PENDING": "bg-warning text-dark",
            "DRAFT": "bg-secondary",
            "VERIFIED": "bg-success",
            "REJECTED": "bg-danger",
        }
        cls = badges.get(status, "bg-secondary")
        return Markup(f'<span class="badge {cls}">{status.replace("_", " ")}</span>')

    @app.template_filter("rag_badge")
    def rag_badge_filter(classification):
        if classification == "COMPLIANT":
            return Markup('<span class="badge bg-success px-2 py-1"><i class="fa-solid fa-circle-check me-1"></i>Compliant</span>')
        elif classification == "MODERATE_RISK":
            return Markup('<span class="badge bg-warning text-dark px-2 py-1"><i class="fa-solid fa-triangle-exclamation me-1"></i>Moderate Risk</span>')
        elif classification == "HIGH_RISK":
            return Markup('<span class="badge bg-danger px-2 py-1"><i class="fa-solid fa-shield-xmark me-1"></i>High Risk</span>')
        return Markup(f'<span class="badge bg-secondary px-2 py-1">{classification or "N/A"}</span>')

    @app.template_filter("score_color")
    def score_color_filter(score):
        if score is None:
            return "text-muted"
        if score >= 80.0:
            return "text-success"
        elif score >= 50.0:
            return "text-warning"
        return "text-danger"

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # CLI Commands
    @app.cli.command("init-db")
    def init_db_cmd():
        """Creates all database tables."""
        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db_cmd():
        """Seeds roles, scoring policies, and Kenya statutory requirements."""
        from app.services.seed_data import seed_roles_and_permissions, seed_scoring_policy, seed_regulatory_content
        print("Seeding roles and permissions...")
        seed_roles_and_permissions()
        print("Seeding scoring policy...")
        seed_scoring_policy()
        print("Seeding Kenya statutory regulatory content (Data Protection, Tax, Labour)...")
        seed_regulatory_content()
        print("Database seeded successfully.")

    @app.cli.command("seed-samples")
    def seed_samples_cmd():
        """Seeds the 4 complete synthetic SME scenarios."""
        from app.services.seed_sample_smes import seed_synthetic_smes
        print("Seeding synthetic SME scenarios...")
        seed_synthetic_smes()
        print("Synthetic SMEs seeded.")

    @app.cli.command("create-admin")
    def create_admin_cmd():
        """Creates the initial super administrator account from configuration."""
        from app.services.seed_data import seed_roles_and_permissions
        seed_roles_and_permissions()
        admin_email = app.config["INITIAL_ADMIN_EMAIL"]
        admin_pw = app.config["INITIAL_ADMIN_PASSWORD"]
        admin_name = app.config["INITIAL_ADMIN_NAME"]

        user = User.query.filter_by(email=admin_email).first()
        super_role = Role.query.filter_by(name=Role.SUPER_ADMIN).first()

        if not user:
            user = User(
                email=admin_email,
                full_name=admin_name,
                is_active=True,
                is_verified=True,
            )
            user.set_password(admin_pw)
            db.session.add(user)
            db.session.flush()

            if super_role:
                db.session.add(UserRole(user_id=user.id, role_id=super_role.id))
            db.session.commit()
            print(f"Super Administrator created: {admin_email}")
        else:
            if super_role and not UserRole.query.filter_by(user_id=user.id, role_id=super_role.id).first():
                db.session.add(UserRole(user_id=user.id, role_id=super_role.id))
                db.session.commit()
            print(f"Super Administrator {admin_email} already exists.")

    return app
