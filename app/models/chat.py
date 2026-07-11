
"""Database models – Chat"""

import datetime
from app import db


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), default="New Conversation")
    language = db.Column(db.String(10), default="en")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False)
    message_count = db.Column(db.Integer, default=0)

    messages = db.relationship("ChatMessage", backref="session", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "language": self.language,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), default="en")
    retrieved_docs = db.Column(db.JSON, nullable=True)   # RAG sources used
    confidence = db.Column(db.Float, nullable=True)
    feedback_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    tokens_used = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "language": self.language,
            "retrieved_docs": self.retrieved_docs,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "tokens_used": self.tokens_used,
        }
