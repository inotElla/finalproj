from flask import Blueprint, jsonify, render_template
from flask_login import login_required

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "C.A.T.E.R"})

@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")