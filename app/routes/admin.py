
"""
Admin routes – document management, knowledge base, analytics
"""

import os
import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.document import Document
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.feedback import Feedback
from app.services.rag_service import get_rag_pipeline

admin_bp = Blueprint("admin", __name__)

ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx", "csv"}


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            if request.is_json:
                return jsonify({"error": "Admin access required"}), 403
            flash("Admin access required", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route("/")
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_docs = Document.query.count()
    total_messages = ChatMessage.query.count()
    total_sessions = ChatSession.query.count()
    avg_feedback = db.session.query(db.func.avg(Feedback.rating)).scalar() or 0
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    rag = get_rag_pipeline()
    rag_stats = rag.get_collection_stats()

    return render_template("admin/dashboard.html",
        total_users=total_users,
        total_docs=total_docs,
        total_messages=total_messages,
        total_sessions=total_sessions,
        avg_feedback=round(float(avg_feedback), 1),
        recent_users=recent_users,
        rag_stats=rag_stats,
    )


@admin_bp.route("/documents")
@login_required
@admin_required
def documents():
    docs = Document.query.order_by(Document.created_at.desc()).all()
    return render_template("admin/documents.html", documents=docs)


@admin_bp.route("/documents/upload", methods=["POST"])
@login_required
@admin_required
def upload_document():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    upload_dir = os.getenv("UPLOAD_FOLDER", "data/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    doc = Document(
        title=request.form.get("title", filename),
        filename=filename,
        file_path=file_path,
        file_type=filename.rsplit(".", 1)[1].lower(),
        source_url=request.form.get("source_url", ""),
        source_name=request.form.get("source_name", ""),
        category=request.form.get("category", "general"),
        language=request.form.get("language", "en"),
        file_size=os.path.getsize(file_path),
        uploaded_by=current_user.id,
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify({"success": True, "document": doc.to_dict()})


@admin_bp.route("/documents/<int:doc_id>/index", methods=["POST"])
@login_required
@admin_required
def index_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    rag = get_rag_pipeline()

    metadata = {
        "document_id": str(doc.id),
        "title": doc.title,
        "source_name": doc.source_name or "Knowledge Base",
        "source_url": doc.source_url or "",
        "category": doc.category or "general",
        "language": doc.language or "en",
    }

    success, chunk_count = rag.index_document(doc.file_path, metadata)
    if success:
        doc.is_indexed = True
        doc.chunk_count = chunk_count
        doc.indexed_at = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True, "chunk_count": chunk_count})

    return jsonify({"success": False, "message": "Indexing failed"}), 500


@admin_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    rag = get_rag_pipeline()
    rag.delete_document_chunks(str(doc.id))

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.session.delete(doc)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    # Message stats per day (last 30 days)
    from sqlalchemy import func
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)

    daily_messages = db.session.query(
        func.date(ChatMessage.created_at).label("date"),
        func.count(ChatMessage.id).label("count"),
    ).filter(
        ChatMessage.created_at >= thirty_days_ago,
        ChatMessage.role == "user",
    ).group_by(func.date(ChatMessage.created_at)).all()

    feedback_dist = db.session.query(
        Feedback.rating,
        func.count(Feedback.id).label("count"),
    ).group_by(Feedback.rating).all()

    return jsonify({
        "daily_messages": [{"date": str(r.date), "count": r.count} for r in daily_messages],
        "feedback_distribution": [{"rating": r.rating, "count": r.count} for r in feedback_dist],
        "total_users": User.query.count(),
        "active_users": User.query.filter(
            User.last_login >= thirty_days_ago
        ).count(),
    })


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/feedback")
@login_required
@admin_required
def feedbacks():
    all_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(100).all()
    return render_template("admin/feedback.html", feedbacks=all_feedback)


@admin_bp.route("/knowledge-base")
@login_required
@admin_required
def knowledge_base():
    rag = get_rag_pipeline()
    stats = rag.get_collection_stats()
    return render_template("admin/knowledge_base.html", rag_stats=stats)


@admin_bp.route("/seed-knowledge", methods=["POST"])
@login_required
@admin_required
def seed_knowledge():
    """Seed knowledge base with built-in financial content."""
    rag = get_rag_pipeline()
    seeded = _seed_financial_knowledge(rag)
    return jsonify({"success": True, "documents_seeded": seeded})


def _seed_financial_knowledge(rag) -> int:
    """Seed the vector DB with curated financial literacy content."""
    knowledge_items = [
        {
            "title": "UPI Payments Guide",
            "content": """UPI (Unified Payments Interface) is a real-time payment system developed by NPCI.
Key features: Send/receive money 24x7, use mobile number or VPA (Virtual Payment Address).
Popular UPI apps: BHIM, PhonePe, Google Pay, Paytm, Amazon Pay.
Transaction limit: ₹1 lakh per transaction (₹2 lakh for verified users).
Safety tips: Never share UPI PIN with anyone. Verify recipient's name before paying.
UPI ID format: mobilenumber@upi or name@bankname.
To receive money, you never need to enter PIN. If asked for PIN to receive money, it's a SCAM.
Source: NPCI - npci.org.in""",
            "category": "payments",
            "source_name": "NPCI - National Payments Corporation of India",
            "source_url": "https://npci.org.in",
        },
        {
            "title": "Digital Banking Security",
            "content": """RBI Guidelines on Digital Banking Security:
1. Never share OTP, PIN, CVV, or password with anyone - not even bank employees.
2. Always check the URL is the official bank website (https://www.sbi.co.in etc.)
3. Register mobile number with bank for transaction alerts.
4. Use strong passwords and enable 2-factor authentication.
5. Report fraud immediately: Call 1930 (Cyber Crime Helpline) or cybercrime.gov.in
6. Your bank will NEVER ask for OTP or password via phone or email.
7. Phishing: Fake emails/SMS pretending to be bank. Always log in directly to bank website.
8. If you suspect fraud, immediately call bank's 24x7 helpline and block your account/card.
Source: RBI - rbi.org.in/financialeducation""",
            "category": "security",
            "source_name": "Reserve Bank of India",
            "source_url": "https://rbi.org.in",
        },
        {
            "title": "Jan Dhan Yojana - Financial Inclusion",
            "content": """Pradhan Mantri Jan Dhan Yojana (PMJDY) - World's largest financial inclusion program.
Benefits: Zero-balance savings account, RuPay debit card, ₹2 lakh accident insurance (RuPay card holders).
₹10,000 overdraft facility after 6 months of satisfactory operation.
Life insurance of ₹30,000 for accounts opened before Jan 2015.
How to open: Visit any bank branch with Aadhaar card and one photo.
Eligible: All Indian citizens above 10 years of age.
No minimum balance required. No charges for basic services.
More than 530 million accounts opened as of 2024.
Source: pmjdy.gov.in, Ministry of Finance""",
            "category": "banking",
            "source_name": "PMJDY - Ministry of Finance",
            "source_url": "https://pmjdy.gov.in",
        },
        {
            "title": "Mutual Funds SIP Basics",
            "content": """SIP (Systematic Investment Plan) - Invest a fixed amount monthly in mutual funds.
Minimum SIP: ₹100-₹500/month depending on fund.
Benefits: Rupee cost averaging, power of compounding, disciplined savings.
Types: Equity funds (high return, high risk), Debt funds (stable), Hybrid funds (balanced).
ELSS funds: Tax saving under 80C with 3-year lock-in.
How to start: Use SEBI-registered platforms (Zerodha, Groww, Kuvera) or bank branches.
Important: Mutual fund investments are subject to market risk. Read all scheme documents carefully.
SEBI registration is mandatory for mutual fund distributors.
Source: SEBI - sebi.gov.in, AMFI - amfiindia.com""",
            "category": "investment",
            "source_name": "SEBI - Securities and Exchange Board of India",
            "source_url": "https://sebi.gov.in",
        },
        {
            "title": "Income Tax Filing Guide India",
            "content": """Income Tax in India - Financial Year 2024-25:
New Tax Regime (Default): 0-3L: NIL, 3-7L: 5%, 7-10L: 10%, 10-12L: 15%, 12-15L: 20%, 15L+: 30%.
Standard deduction: ₹75,000 under new regime.
Old Regime: Allows deductions - 80C (₹1.5L), 80D (health insurance ₹25K), HRA, LTA.
Key deductions 80C: PPF, ELSS, LIC premium, EPF, NSC, home loan principal.
ITR filing deadline: July 31 (salaried), October 31 (audited businesses).
File at: incometaxindia.gov.in
Form 16: Given by employer showing TDS deducted.
PAN card mandatory for transactions above ₹50,000.
Source: Income Tax Department - incometaxindia.gov.in""",
            "category": "taxation",
            "source_name": "Income Tax Department of India",
            "source_url": "https://incometaxindia.gov.in",
        },
    ]

    count = 0
    for item in knowledge_items:
        success, _ = rag.index_text(
            text=item["content"],
            metadata={
                "title": item["title"],
                "category": item["category"],
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "document_id": f"seed_{count}",
            },
        )
        if success:
            count += 1
    return count
