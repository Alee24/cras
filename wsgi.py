import os
from app import create_app, db
from app.services.seed_data import seed_roles_and_permissions, seed_scoring_policy, seed_regulatory_content
from app.services.live_demo_generator import populate_comprehensive_live_data
from app.models.auth import User, Role, UserRole

app = create_app(os.environ.get("FLASK_ENV", "default"))

with app.app_context():
    db.create_all()
    seed_roles_and_permissions()
    seed_scoring_policy()
    seed_regulatory_content()
    
    # Auto-seed default Super Admin if configured and not present
    admin_email = app.config.get("INITIAL_ADMIN_EMAIL", "admin@cras.ke")
    admin_pw = app.config.get("INITIAL_ADMIN_PASSWORD", "Admin@CRAS2026!")
    admin_name = app.config.get("INITIAL_ADMIN_NAME", "System Administrator")
    
    existing_admin = User.query.filter_by(email=admin_email).first()
    super_role = Role.query.filter_by(name=Role.SUPER_ADMIN).first()
    if not existing_admin:
        admin_user = User(
            email=admin_email,
            full_name=admin_name,
            is_active=True,
            is_verified=True,
        )
        admin_user.set_password(admin_pw)
        db.session.add(admin_user)
        db.session.flush()
        if super_role:
            db.session.add(UserRole(user_id=admin_user.id, role_id=super_role.id))
        db.session.commit()

    # Populate and ensure all 4 Kenyan SME scenarios have complete live data on every boot
    populate_comprehensive_live_data(app.config.get("UPLOAD_FOLDER", "uploads"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
