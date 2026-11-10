import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Guarantee instance and uploads directories exist
(BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "uploads").mkdir(parents=True, exist_ok=True)

# Load .env if present
load_dotenv(BASE_DIR / ".env")


def get_database_uri() -> str:
    """
    Resolves database connection URI from environment variables with intelligent fallbacks.
    Supports:
      1. DATABASE_URL (SQLite or PostgreSQL)
      2. DB_TYPE / DB_NAME shorthand
      3. Default fallback to local SQLite in instance/cras.db
    Automatically creates parent directories for SQLite files and normalizes paths as POSIX
    to prevent 'sqlite3.OperationalError: unable to open database file' on Windows.
    """
    db_url = os.environ.get("DATABASE_URL", "").strip()

    if not db_url:
        db_type = os.environ.get("DB_TYPE", "sqlite").strip().lower()
        if db_type == "sqlite":
            db_name = os.environ.get("DB_NAME", "cras.db").strip()
            instance_dir = (BASE_DIR / "instance").resolve()
            instance_dir.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{ (instance_dir / db_name).as_posix() }"
        elif db_type in ("postgres", "postgresql"):
            db_user = os.environ.get("DB_USER", "cras_user")
            db_pass = os.environ.get("DB_PASSWORD", "cras_secure_password_2026")
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5432")
            db_name = os.environ.get("DB_NAME", "cras_db")
            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        else:
            instance_dir = (BASE_DIR / "instance").resolve()
            instance_dir.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{ (instance_dir / 'cras.db').as_posix() }"

    # Normalize Heroku/Render/AWS legacy postgres:// scheme to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # If SQLite file path, ensure parent directory exists and ALWAYS use POSIX slashes
    if db_url.startswith("sqlite:///"):
        raw_path = db_url.replace("sqlite:///", "", 1)
        if raw_path != ":memory:":
            file_path = Path(raw_path)
            if not file_path.is_absolute():
                file_path = (BASE_DIR / raw_path).resolve()
            else:
                file_path = file_path.resolve()
            
            # Ensure folder exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use forward slashes (as_posix) so Windows backslashes never corrupt the URI
            db_url = f"sqlite:///{file_path.as_posix()}"

    return db_url


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "cras-dev-insecure-secret-key-replace-in-production")
    
    # Database
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    } if not SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}

    # File Uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)) # 16 MB
    ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "jpg", "jpeg", "png"}

    # Sessions & Security
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", 28800))) # 8 hours
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "t")

    # Rate Limiting & Auth Controls
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_MINUTES = 15

    # System Default Admin
    INITIAL_ADMIN_EMAIL = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@cras.ke")
    INITIAL_ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD", "Admin@CRAS2026!")
    INITIAL_ADMIN_NAME = os.environ.get("INITIAL_ADMIN_NAME", "System Administrator")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

