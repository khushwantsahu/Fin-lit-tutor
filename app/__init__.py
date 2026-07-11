
"""
Digital Financial Literacy Agent
Flask Application Factory
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv

# Resolve absolute path to .env file relative to the project root (one level up from this app/ directory)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
_env_path = os.path.join(_project_root, ".env")
load_dotenv(_env_path)

# ── Extension instances ────────────────────────────────────────
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
sess = Session()


def create_app(config_name: str = None) -> Flask:
    """Application factory."""
    # ── Resolve project root (the folder that contains app.py) ─
    # app/__init__.py is two levels below the project root when
    # installed as a package, but one level below when the package
    # folder is named "app".  We use the directory that contains
    # the "app" package folder as the project root.
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # ── Ensure all required directories exist FIRST ───────────
    # This must happen before any SQLAlchemy / Flask-Session
    # configuration so the database file path is valid.
    for rel in [
        "data/uploads", "data/chroma_db", "data/sessions",
        "data/knowledge_base", "instance", "logs",
    ]:
        os.makedirs(os.path.join(BASE_DIR, rel), exist_ok=True)

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )

    # ── Build an absolute SQLite URI so it works regardless of CWD
    _default_db = "sqlite:///" + os.path.join(BASE_DIR, "instance", "finliteracy.db")
    _db_url = os.getenv("DATABASE_URL", _default_db)
    # If the env var still uses a relative sqlite URI, make it absolute too.
    if _db_url.startswith("sqlite:///") and not _db_url.startswith("sqlite:////"):
        _rel = _db_url[len("sqlite:///"):]
        if not os.path.isabs(_rel):
            _db_url = "sqlite:///" + os.path.join(BASE_DIR, _rel)

    # ── Configuration ──────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "data/uploads"))
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 16777216))
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(BASE_DIR, "data", "sessions")
    app.config["PERMANENT_SESSION_LIFETIME"] = int(os.getenv("PERMANENT_SESSION_LIFETIME", 86400))

    # ── Initialize extensions ──────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    sess.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # ── Register Blueprints ────────────────────────────────────
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.modules import modules_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(modules_bp, url_prefix="/modules")

    # ── Logging setup ──────────────────────────────────────────
    if not app.debug:
        os.makedirs("logs", exist_ok=True)
        handler = RotatingFileHandler("logs/app.log", maxBytes=10485760, backupCount=10)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Fin-Lit-Tutor Digital Financial Literacy Agent started")

    # ── Create DB tables ───────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin(app)
        _warm_up_rag(app)

    return app


def _seed_admin(app: Flask) -> None:
    """Create default admin user on first run."""
    from app.models.user import User
    admin_email = os.getenv("ADMIN_EMAIL", "REDACTED_EMAIL")
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name=os.getenv("ADMIN_NAME", "System Admin"),
            email=admin_email,
            is_admin=True,
            language="en",
        )
        admin.set_password(os.getenv("ADMIN_PASSWORD", "REDACTED_PASSWORD"))
        db.session.add(admin)
        db.session.commit()
        app.logger.info(f"Admin user created: {admin_email}")


def _warm_up_rag(app: Flask) -> None:
    """Eagerly initialize the RAG pipeline at startup.

    Calling get_rag_pipeline() here — inside create_app()'s app_context —
    ensures the singleton is built once in the main process before any
    request arrives.  This prevents a 7-10 second IBM network handshake
    from happening mid-request, and guarantees the pipeline is ready
    regardless of Flask's debug/reloader mode.
    """
    try:
        from app.services.rag_service import get_rag_pipeline
        rag = get_rag_pipeline()
        if rag._initialized:
            app.logger.info("RAG pipeline warm-up complete — ready")
        else:
            app.logger.warning(
                f"RAG pipeline warm-up complete — fallback mode. "
                f"Initialization error:\n{getattr(rag, 'init_error', 'No detailed error captured.')}"
            )
    except Exception as exc:
        # Never let RAG startup crash the whole app.
        app.logger.warning(f"RAG pipeline warm-up failed (non-fatal): {exc}")
