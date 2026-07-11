
"""
API routes – financial tools, EMI, budget, health score, analytics
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.services.financial_service import FinancialCalculator
from app.models.progress import UserProgress, Achievement

api_bp = Blueprint("api", __name__)
calc = FinancialCalculator()


# ── EMI Calculator ─────────────────────────────────────────────
@api_bp.route("/emi", methods=["POST"])
@login_required
def calculate_emi():
    data = request.get_json()
    try:
        result = calc.calculate_emi(
            principal=float(data["principal"]),
            annual_rate=float(data["annual_rate"]),
            tenure_months=int(data["tenure_months"]),
        )
        return jsonify({"success": True, "data": result})
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── Budget Planner ─────────────────────────────────────────────
@api_bp.route("/budget", methods=["POST"])
@login_required
def calculate_budget():
    data = request.get_json()
    try:
        result = calc.budget_50_30_20(float(data["monthly_income"]))
        return jsonify({"success": True, "data": result})
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── Financial Health Score ─────────────────────────────────────
@api_bp.route("/health-score", methods=["POST"])
@login_required
def calculate_health_score():
    data = request.get_json()
    try:
        result = calc.calculate_health_score(data)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── SIP Calculator ─────────────────────────────────────────────
@api_bp.route("/sip", methods=["POST"])
@login_required
def calculate_sip():
    data = request.get_json()
    try:
        result = calc.calculate_sip(
            monthly_sip=float(data["monthly_sip"]),
            annual_rate=float(data["annual_rate"]),
            years=int(data["years"]),
        )
        return jsonify({"success": True, "data": result})
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── User Analytics ─────────────────────────────────────────────
@api_bp.route("/analytics/user")
@login_required
def user_analytics():
    from app.models.chat import ChatSession, ChatMessage
    sessions = ChatSession.query.filter_by(user_id=current_user.id).count()
    messages = ChatMessage.query.join(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatMessage.role == "user"
    ).count()
    progress = UserProgress.query.filter_by(user_id=current_user.id, completed=True).count()
    achievements = Achievement.query.filter_by(user_id=current_user.id).count()
    return jsonify({
        "total_sessions": sessions,
        "total_messages": messages,
        "completed_topics": progress,
        "achievements": achievements,
        "xp_points": current_user.xp_points or 0,
        "financial_level": current_user.financial_level,
    })


# ── Progress Tracker ───────────────────────────────────────────
@api_bp.route("/progress", methods=["GET"])
@login_required
def get_progress():
    progress = UserProgress.query.filter_by(user_id=current_user.id).all()
    return jsonify([p.to_dict() for p in progress])


@api_bp.route("/progress", methods=["POST"])
@login_required
def update_progress():
    data = request.get_json()
    prog = UserProgress.query.filter_by(
        user_id=current_user.id,
        module=data["module"],
        topic=data["topic"],
    ).first()
    if not prog:
        prog = UserProgress(
            user_id=current_user.id,
            module=data["module"],
            topic=data["topic"],
        )
        db.session.add(prog)

    prog.completed = data.get("completed", False)
    prog.score = data.get("score", 0)
    if prog.completed:
        import datetime
        prog.completed_at = datetime.datetime.utcnow()
        current_user.xp_points = (current_user.xp_points or 0) + 10

    db.session.commit()
    return jsonify({"success": True, "data": prog.to_dict()})


# ── Scam Checker ───────────────────────────────────────────────
@api_bp.route("/scam-check", methods=["POST"])
@login_required
def scam_check():
    from app.agent_instructions import is_scam_message
    data = request.get_json()
    text = data.get("text", "")
    is_scam = is_scam_message(text)
    response = jsonify({
        "is_potential_scam": is_scam,
        "warning": "⚠️ This message shows signs of a financial scam!" if is_scam else None,
        "helpline": "1930" if is_scam else None,
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ── Government Schemes ─────────────────────────────────────────
@api_bp.route("/schemes")
def get_schemes():
    schemes = [
        {"name": "PMJDY", "full_name": "Pradhan Mantri Jan Dhan Yojana", "desc": "Zero-balance savings account with RuPay debit card, ₹1 lakh accident insurance.", "url": "https://pmjdy.gov.in", "category": "banking", "benefit": "Free account"},
        {"name": "PMJJBY", "full_name": "PM Jeevan Jyoti Bima Yojana", "desc": "Life insurance of ₹2 lakh at just ₹436/year for ages 18-50.", "url": "https://jansuraksha.gov.in", "category": "insurance", "benefit": "₹2 lakh life cover"},
        {"name": "PMSBY", "full_name": "PM Suraksha Bima Yojana", "desc": "Accidental insurance ₹2 lakh at ₹20/year for ages 18-70.", "url": "https://jansuraksha.gov.in", "category": "insurance", "benefit": "₹2 lakh accident cover"},
        {"name": "APY", "full_name": "Atal Pension Yojana", "desc": "Guaranteed pension of ₹1000-₹5000/month after age 60.", "url": "https://npscra.nsdl.co.in", "category": "pension", "benefit": "Guaranteed pension"},
        {"name": "MUDRA", "full_name": "Pradhan Mantri MUDRA Yojana", "desc": "Loans up to ₹10 lakh for micro and small enterprises without collateral.", "url": "https://mudra.org.in", "category": "loan", "benefit": "Up to ₹10 lakh loan"},
        {"name": "PM Kisan", "full_name": "PM Kisan Samman Nidhi", "desc": "₹6000/year income support to small and marginal farmers.", "url": "https://pmkisan.gov.in", "category": "agriculture", "benefit": "₹6000/year"},
        {"name": "Ayushman Bharat", "full_name": "PM-JAY (PMJAY)", "desc": "Health insurance of ₹5 lakh/year per family for hospital treatment.", "url": "https://pmjay.gov.in", "category": "health", "benefit": "₹5 lakh health cover"},
        {"name": "SSY", "full_name": "Sukanya Samriddhi Yojana", "desc": "High-interest savings scheme for girl child (7.6% p.a.), tax-free.", "url": "https://indiapost.gov.in", "category": "savings", "benefit": "7.6% returns"},
        {"name": "PPF", "full_name": "Public Provident Fund", "desc": "Safe 15-year investment with 7.1% tax-free returns and ₹1.5L 80C deduction.", "url": "https://indiapost.gov.in", "category": "savings", "benefit": "7.1% tax-free"},
        {"name": "NPS", "full_name": "National Pension System", "desc": "Market-linked pension scheme with extra ₹50,000 tax deduction under 80CCD(1B).", "url": "https://npscra.nsdl.co.in", "category": "pension", "benefit": "Extra ₹50K tax benefit"},
        {"name": "Stand Up India", "full_name": "Stand Up India Scheme", "desc": "Loans ₹10L-₹1Cr for SC/ST/Women entrepreneurs for greenfield projects.", "url": "https://standupmitra.in", "category": "business", "benefit": "Up to ₹1 crore"},
        {"name": "SVANidhi", "full_name": "PM Street Vendor's AtmaNirbhar Nidhi", "desc": "Micro-credit loans for street vendors starting from ₹10,000.", "url": "https://pmsvanidhi.mohua.gov.in", "category": "loan", "benefit": "₹10,000 to ₹50,000"},
    ]
    category = request.args.get("category")
    if category:
        schemes = [s for s in schemes if s["category"] == category]
    return jsonify(schemes)


# ── RAG / LLM Health ───────────────────────────────────────────
@api_bp.route("/diag")
@login_required
def rag_diag():
    """Diagnostic endpoint — reports live RAG pipeline state.
    Accessible to any logged-in user at /api/diag.
    """
    from app.services import rag_service as rag_mod
    rag = rag_mod.get_rag_pipeline()
    return jsonify({
        "initialized": rag._initialized,
        "retrieval_ready": rag._retrieval_ready,
        "model_id": getattr(rag, "model_id", None),
        "has_watsonx_model": getattr(rag, "watsonx_model", None) is not None,
        "has_llm": rag.llm is not None,
        "singleton_id": id(rag),
        "module_id": id(rag_mod),
        "init_error": getattr(rag, "init_error", None),
    })
