"""Study Sync: Flask application (REST API + pages)."""
import re
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import analytics
import db
from config import Config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COLOUR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
PALETTE = ["#2A9D8F", "#1F3A5F", "#E9A23B", "#8E6BBF", "#D1495B", "#3A86FF"]


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    if test_config:
        app.config.update(test_config)
    db.init_app(app)

    @app.cli.command("init-db")
    def init_db_cmd():
        db.init_db()
        print("Database initialised.")

    # ---------- helpers ----------
    def err(msg, code=400):
        return jsonify({"error": msg}), code

    def login_required(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if "user_id" not in session:
                if request.path.startswith("/api/"):
                    return err("Authentication required", 401)
                return redirect(url_for("login"))
            return f(*a, **kw)
        return wrapper

    def client_today():
        raw = request.args.get("today")
        try:
            return date.fromisoformat(raw) if raw else date.today()
        except ValueError:
            return date.today()

    def parse_start(raw):
        try:
            return datetime.strptime(raw, "%Y-%m-%dT%H:%M")
        except (TypeError, ValueError):
            return None

    def valid_minutes(v):
        return isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 720

    def owns_subject(uid, sid):
        return db.query("SELECT 1 AS x FROM subjects WHERE subject_id = ? AND user_id = ?",
                        (sid, uid), one=True) is not None

    # ---------- pages / auth ----------
    @app.route("/")
    def index():
        return redirect(url_for("dashboard" if "user_id" in session else "login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("auth.html", mode="register")
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        if not EMAIL_RE.match(email) or len(pw) < 8:
            return render_template("auth.html", mode="register",
                                   error="Enter a valid email and a password of 8+ characters."), 400
        if db.query("SELECT 1 AS x FROM users WHERE email = ?", (email,), one=True):
            return render_template("auth.html", mode="register",
                                   error="That email is already registered."), 409
        uid, _ = db.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                            (email, generate_password_hash(pw)))
        db.execute("INSERT INTO subjects (user_id, name, colour) VALUES (?, ?, ?)",
                   (uid, "General Study", PALETTE[0]))
        session.clear()
        session.permanent = True
        session["user_id"], session["email"] = uid, email
        return redirect(url_for("dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("auth.html", mode="login")
        email = request.form.get("email", "").strip().lower()
        user = db.query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if not user or not check_password_hash(user["password_hash"], request.form.get("password", "")):
            return render_template("auth.html", mode="login", error="Incorrect email or password."), 401
        session.clear()
        session.permanent = True
        session["user_id"], session["email"] = user["user_id"], user["email"]
        return redirect(url_for("dashboard"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", email=session["email"])

    # ---------- subjects ----------
    @app.route("/api/subjects", methods=["GET", "POST"])
    @login_required
    def subjects():
        uid = session["user_id"]
        if request.method == "GET":
            return jsonify(db.query("SELECT subject_id, name, colour FROM subjects "
                                    "WHERE user_id = ? ORDER BY name", (uid,)))
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        colour = data.get("colour") or PALETTE[len(db.query(
            "SELECT 1 FROM subjects WHERE user_id = ?", (uid,))) % len(PALETTE)]
        if not 1 <= len(name) <= 100:
            return err("Subject name must be 1-100 characters.")
        if not COLOUR_RE.match(colour):
            return err("Colour must be a hex value such as #2A9D8F.")
        if db.query("SELECT 1 AS x FROM subjects WHERE user_id = ? AND name = ?", (uid, name), one=True):
            return err("Subject already exists.", 409)
        sid, _ = db.execute("INSERT INTO subjects (user_id, name, colour) VALUES (?, ?, ?)",
                            (uid, name, colour))
        return jsonify({"subject_id": sid, "name": name, "colour": colour}), 201

    # ---------- sessions (CRUD) ----------
    @app.route("/api/sessions", methods=["GET", "POST"])
    @login_required
    def sessions():
        uid = session["user_id"]
        if request.method == "GET":
            sql = ("SELECT s.session_id, s.subject_id, sub.name AS subject, sub.colour, "
                   "s.start_time, s.minutes FROM sessions s JOIN subjects sub "
                   "ON sub.subject_id = s.subject_id WHERE s.user_id = ?")
            params = [uid]
            if request.args.get("subject_id", type=int):
                sql += " AND s.subject_id = ?"
                params.append(request.args.get("subject_id", type=int))
            limit = min(request.args.get("limit", 15, type=int), 200)
            sql += " ORDER BY s.start_time DESC LIMIT %d" % max(limit, 1)
            rows = db.query(sql, tuple(params))
            for r in rows:
                r["start_time"] = str(r["start_time"])[:16].replace(" ", "T")
            return jsonify(rows)
        data = request.get_json(silent=True) or {}
        start = parse_start(data.get("start_time"))
        if start is None:
            return err("start_time must look like 2026-09-02T16:00.")
        if not valid_minutes(data.get("minutes")):
            return err("minutes must be a whole number from 1 to 720.")
        if not isinstance(data.get("subject_id"), int) or not owns_subject(uid, data["subject_id"]):
            return err("Unknown subject.", 404)
        sid, _ = db.execute("INSERT INTO sessions (user_id, subject_id, start_time, minutes) "
                            "VALUES (?, ?, ?, ?)",
                            (uid, data["subject_id"], start.strftime("%Y-%m-%d %H:%M:%S"), data["minutes"]))
        return jsonify({"session_id": sid}), 201

    @app.route("/api/sessions/<int:sid>", methods=["PUT", "DELETE"])
    @login_required
    def session_item(sid):
        uid = session["user_id"]
        row = db.query("SELECT session_id FROM sessions WHERE session_id = ? AND user_id = ?",
                       (sid, uid), one=True)
        if not row:
            return err("Session not found.", 404)
        if request.method == "DELETE":
            db.execute("DELETE FROM sessions WHERE session_id = ? AND user_id = ?", (sid, uid))
            return jsonify({"deleted": sid})
        data = request.get_json(silent=True) or {}
        start = parse_start(data.get("start_time"))
        if start is None:
            return err("start_time must look like 2026-09-02T16:00.")
        if not valid_minutes(data.get("minutes")):
            return err("minutes must be a whole number from 1 to 720.")
        if not isinstance(data.get("subject_id"), int) or not owns_subject(uid, data["subject_id"]):
            return err("Unknown subject.", 404)
        db.execute("UPDATE sessions SET subject_id = ?, start_time = ?, minutes = ? "
                   "WHERE session_id = ? AND user_id = ?",
                   (data["subject_id"], start.strftime("%Y-%m-%d %H:%M:%S"), data["minutes"], sid, uid))
        return jsonify({"updated": sid})

    # ---------- goals ----------
    @app.route("/api/goals", methods=["GET", "POST"])
    @login_required
    def goals():
        uid = session["user_id"]
        if request.method == "GET":
            return jsonify({"weekly": analytics.get_goal(uid, "weekly"),
                            "monthly": analytics.get_goal(uid, "monthly")})
        data = request.get_json(silent=True) or {}
        period, hours = data.get("period"), data.get("target_hours")
        if period not in ("weekly", "monthly"):
            return err("period must be 'weekly' or 'monthly'.")
        limit = 168 if period == "weekly" else 744
        if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not 0 < hours <= limit:
            return err("target_hours must be greater than 0 and at most %d." % limit)
        if db.query("SELECT 1 AS x FROM goals WHERE user_id = ? AND period = ?", (uid, period), one=True):
            db.execute("UPDATE goals SET target_hours = ? WHERE user_id = ? AND period = ?",
                       (hours, uid, period))
        else:
            db.execute("INSERT INTO goals (user_id, period, target_hours) VALUES (?, ?, ?)",
                       (uid, period, hours))
        return jsonify({"period": period, "target_hours": hours})

       # ---------- reporting ----------
    @app.route("/api/summary")
    @login_required
    def api_summary():
        subject_id = request.args.get("subject_id", type=int)

        return jsonify(
            analytics.summary(
                session["user_id"],
                client_today(),
                subject_id
            )
        )

    @app.route("/api/chart/weekly")
    @login_required
    def api_weekly():
        subject_id = request.args.get("subject_id", type=int)

        return jsonify(
            analytics.weekly_chart(
                session["user_id"],
                client_today(),
                subject_id
            )
        )

    @app.route("/api/chart/monthly")
    @login_required
    def api_monthly():
        subject_id = request.args.get("subject_id", type=int)

        return jsonify(
            analytics.monthly_chart(
                session["user_id"],
                client_today(),
                subject_id=subject_id
            )
        )

    return app
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
