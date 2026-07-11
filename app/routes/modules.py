
"""
Module routes – Budget Planner, Loan Calculator, Health Score,
Scam Awareness, Government Resources, Learning Dashboard
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user

modules_bp = Blueprint("modules", __name__)


@modules_bp.route("/budget-planner")
@login_required
def budget_planner():
    return render_template("modules/budget_planner.html", user=current_user)


@modules_bp.route("/emi-calculator")
@login_required
def emi_calculator():
    return render_template("modules/emi_calculator.html", user=current_user)


@modules_bp.route("/health-score")
@login_required
def health_score():
    return render_template("modules/health_score.html", user=current_user)


@modules_bp.route("/scam-awareness")
@login_required
def scam_awareness():
    return render_template("modules/scam_awareness.html", user=current_user)


@modules_bp.route("/government-schemes")
@login_required
def government_schemes():
    return render_template("modules/government_schemes.html", user=current_user)


@modules_bp.route("/learning")
@login_required
def learning_dashboard():
    return render_template("modules/learning.html", user=current_user)


@modules_bp.route("/achievements")
@login_required
def achievements():
    from app.models.progress import Achievement
    user_achievements = Achievement.query.filter_by(user_id=current_user.id).all()
    return render_template("modules/achievements.html",
        user=current_user,
        achievements=user_achievements
    )
