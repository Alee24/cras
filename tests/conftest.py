import pytest
from app import create_app, db
from app.models.auth import User, Role, UserRole
from app.models.organization import Organization, Department, OrganizationUser
from app.services.seed_data import seed_roles_and_permissions, seed_scoring_policy, seed_regulatory_content


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        seed_roles_and_permissions()
        seed_scoring_policy()
        seed_regulatory_content()
        yield app
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def session(app):
    with app.app_context():
        # Start a nested transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)
        db.session = session

        yield session

        transaction.rollback()
        connection.close()
        session.remove()

