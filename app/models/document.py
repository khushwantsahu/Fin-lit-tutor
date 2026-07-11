
"""Database models – Documents, Feedback, Progress"""

import datetime
from app import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)  # pdf/txt/docx
    source_url = db.Column(db.String(500), nullable=True)
    source_name = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(100), nullable=True)  # rbi/npci/sebi/government
    language = db.Column(db.String(10), default="en")
    chunk_count = db.Column(db.Integer, default=0)
    is_indexed = db.Column(db.Boolean, default=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    indexed_at = db.Column(db.DateTime, nullable=True)
    file_size = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "source_name": self.source_name,
            "category": self.category,
            "chunk_count": self.chunk_count,
            "is_indexed": self.is_indexed,
            "created_at": self.created_at.isoformat(),
        }
