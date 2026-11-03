import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "cras-dev-insecure-secret-key-replace-in-production")
    
    # Database
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'cras.db'}")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    } if not db_url.startswith("sqlite") else {}

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
