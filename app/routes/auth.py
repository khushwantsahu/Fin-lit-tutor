
"""
Authentication routes – register, login, logout, profile
"""

import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        remember = bool(data.get("remember", False))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()

            if request.is_json:
                return jsonify({"success": True, "redirect": url_for("main.dashboard"), "user": user.to_dict()})
            return redirect(request.args.get("next") or url_for("main.dashboard"))

        if request.is_json:
            return jsonify({"success": False, "message": "Invalid email or password"}), 401
        flash("Invalid email or password", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        language = data.get("language", "en")

        if not name or not email or not password:
            msg = "All fields are required"
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("auth/register.html")

        if len(password) < 8:
            msg = "Password must be at least 8 characters"
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            msg = "Email already registered"
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 409
            flash(msg, "danger")
            return render_template("auth/register.html")

        user = User(name=name, email=email, language=language)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        if request.is_json:
            return jsonify({"success": True, "redirect": url_for("main.dashboard"), "user": user.to_dict()}), 201
        flash(f"Welcome, {name}! Your account is ready.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile", methods=["GET", "PUT"])
@login_required
def profile():
    if request.method == "PUT":
        data = request.get_json()
        current_user.name = data.get("name", current_user.name)
        current_user.language = data.get("language", current_user.language)
        current_user.phone = data.get("phone", current_user.phone)
        current_user.financial_level = data.get("financial_level", current_user.financial_level)
        current_user.monthly_income = data.get("monthly_income", current_user.monthly_income)
        db.session.commit()
        return jsonify({"success": True, "user": current_user.to_dict()})

    return render_template("auth/profile.html", user=current_user)


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not current_user.check_password(old_password):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "New password must be at least 8 characters"}), 400

    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({"success": True, "message": "Password updated successfully"})
