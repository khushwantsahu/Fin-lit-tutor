
"""Database models – Feedback"""

import datetime
from app import db


class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id"), nullable=True)
    rating = db.Column(db.Integer, nullable=False)   # 1–5
    comment = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }
