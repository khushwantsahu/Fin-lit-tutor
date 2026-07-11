
"""
Profile route added to main app template
"""

import datetime
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.routes.auth import auth_bp


@auth_bp.route("/profile", methods=["GET"])
@login_required
def profile_page():
    return render_template("auth/profile.html", user=current_user)
