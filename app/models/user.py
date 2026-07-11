
"""Database models – User"""

import datetime
from app import db, bcrypt, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    language = db.Column(db.String(10), default="en")
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    avatar = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    financial_level = db.Column(db.String(20), default="beginner")  # beginner/intermediate/advanced
    monthly_income = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    total_messages = db.Column(db.Integer, default=0)
    xp_points = db.Column(db.Integer, default=0)

    # Relationships
    chat_sessions = db.relationship("ChatSession", backref="user", lazy=True, cascade="all, delete-orphan")
    progress = db.relationship("UserProgress", backref="user", lazy=True, cascade="all, delete-orphan")
    achievements = db.relationship("Achievement", backref="user", lazy=True, cascade="all, delete-orphan")
    feedbacks = db.relationship("Feedback", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "language": self.language,
            "is_admin": self.is_admin,
            "financial_level": self.financial_level,
            "xp_points": self.xp_points,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email}>"
