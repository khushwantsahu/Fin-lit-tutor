
"""
Chat routes – AI conversation, history, feedback
"""

import datetime
import logging
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)
from app import db
from app.models.chat import ChatSession, ChatMessage
from app.models.feedback import Feedback
from app.models.user import User
from app.services.rag_service import get_rag_pipeline
from app.agent_instructions import get_system_prompt

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
@login_required
def chat_page():
    return render_template("chat.html", user=current_user)


@chat_bp.route("/send", methods=["POST"])
@login_required
def send_message():
    data = request.get_json()
    message = (data.get("message") or "").strip()
    session_id = data.get("session_id")
    language = data.get("language", current_user.language or "en")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    # ── Get or create chat session ─────────────────────────────
    if session_id:
        chat_session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    else:
        chat_session = None

    if not chat_session:
        title = message[:60] + ("…" if len(message) > 60 else "")
        chat_session = ChatSession(user_id=current_user.id, title=title, language=language)
        db.session.add(chat_session)
        db.session.flush()

    # ── Load recent history ────────────────────────────────────
    import os
    max_history_turns = int(os.getenv("MAX_CHAT_HISTORY_TURNS", 6))
    recent_messages = ChatMessage.query.filter_by(
        session_id=chat_session.id
    ).order_by(ChatMessage.created_at.desc()).limit(max_history_turns).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(recent_messages)]

    # ── Save user message ──────────────────────────────────────
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=message,
        language=language,
    )
    db.session.add(user_msg)

    # ── Generate AI response ───────────────────────────────────
    rag = get_rag_pipeline()

    try:
        result = rag.generate(
            user_message=message,
            system_prompt=get_system_prompt(),
            chat_history=history,
            language=language,
        )
    except Exception as exc:
        logger.error("Unhandled error in rag.generate: %s", exc, exc_info=True)
        db.session.rollback()
        return jsonify({"error": "AI generation failed unexpectedly. Please try again."}), 500

    # ── Save assistant message ─────────────────────────────────
    ai_msg = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=result["response"],
        language=language,
        retrieved_docs=result.get("retrieved_docs", [])[:3],
        tokens_used=result.get("tokens_used", 0),
    )
    db.session.add(ai_msg)

    # ── Update counters ────────────────────────────────────────
    chat_session.message_count = (chat_session.message_count or 0) + 2
    chat_session.updated_at = datetime.datetime.utcnow()
    current_user.total_messages = (current_user.total_messages or 0) + 1
    current_user.xp_points = (current_user.xp_points or 0) + 5

    db.session.commit()

    return jsonify({
        "response": result["response"],
        "session_id": chat_session.id,
        "message_id": ai_msg.id,
        "retrieved_docs": result.get("retrieved_docs", [])[:3],
        "is_scam_alert": result.get("is_scam_alert", False),
        "tokens_used": result.get("tokens_used", 0),
        # True when IBM Watsonx is unreachable and a static fallback was returned.
        # The frontend can use this flag to show a "⚠️ AI offline" notice.
        "is_fallback": result.get("fallback", False),
    })


@chat_bp.route("/sessions")
@login_required
def get_sessions():
    sessions = ChatSession.query.filter_by(
        user_id=current_user.id, is_archived=False
    ).order_by(ChatSession.updated_at.desc()).limit(20).all()
    return jsonify([s.to_dict() for s in sessions])


@chat_bp.route("/sessions/<int:session_id>/messages")
@login_required
def get_messages(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.created_at).all()
    return jsonify([m.to_dict() for m in messages])


@chat_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    db.session.delete(session)
    db.session.commit()
    return jsonify({"success": True})


@chat_bp.route("/feedback", methods=["POST"])
@login_required
def submit_feedback():
    data = request.get_json()
    feedback = Feedback(
        user_id=current_user.id,
        message_id=data.get("message_id"),
        rating=int(data.get("rating", 3)),
        comment=data.get("comment"),
        category=data.get("category"),
    )
    db.session.add(feedback)

    if data.get("message_id"):
        msg = ChatMessage.query.get(data["message_id"])
        if msg and msg.session.user_id == current_user.id:
            msg.feedback_rating = feedback.rating

    db.session.commit()
    return jsonify({"success": True})
