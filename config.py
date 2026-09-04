import os
import hashlib

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    configured_secret = os.environ.get("SECRET_KEY")
    if not configured_secret and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY must be configured in production.")
    SECRET_KEY = configured_secret or hashlib.sha256(
        (BASE_DIR + ":local-development-key").encode("utf-8")
    ).hexdigest()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database", "idaa.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB max upload

