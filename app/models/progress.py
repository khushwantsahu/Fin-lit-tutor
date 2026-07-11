
"""Database models – User Progress & Achievements"""

import datetime
from app import db


class UserProgress(db.Model):
    __tablename__ = "user_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    module = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "module": self.module,
            "topic": self.topic,
            "completed": self.completed,
            "score": self.score,
        }


class Achievement(db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    badge_icon = db.Column(db.String(50), default="🏆")
    xp_awarded = db.Column(db.Integer, default=50)
    category = db.Column(db.String(100), nullable=True)
    earned_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "badge_icon": self.badge_icon,
            "xp_awarded": self.xp_awarded,
            "earned_at": self.earned_at.isoformat(),
        }
