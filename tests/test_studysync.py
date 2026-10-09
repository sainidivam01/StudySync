"""Automated tests for Study Sync (run:  python -m pytest -v)."""
from datetime import date
import pytest
from conftest import first_subject, log
import analytics

TODAY = "2026-09-02"          # a Wednesday


# ---------- FR1 authentication ----------
def test_register_creates_account_and_redirects(client):
    r = client.post("/register", data={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 302 and "/dashboard" in r.headers["Location"]

def test_register_adds_default_subject(user):
    assert user.get("/api/subjects").get_json()[0]["name"] == "General Study"

@pytest.mark.parametrize("email,pw", [("bad-email", "password123"), ("a@example.com", "short"), ("", "")])
def test_register_rejects_invalid_input(client, email, pw):
    assert client.post("/register", data={"email": email, "password": pw}).status_code == 400

def test_register_rejects_duplicate_email(client):
    d = {"email": "a@example.com", "password": "password123"}
    client.post("/register", data=d)
    client.get("/logout")
    assert client.post("/register", data=d).status_code == 409

def test_password_is_hashed_not_stored_plain(app, user):
    import db
    with app.app_context():
        h = db.query("SELECT password_hash FROM users", one=True)["password_hash"]
    assert "password123" not in h and len(h) > 30

def test_login_success_and_failure(client):
    client.post("/register", data={"email": "a@example.com", "password": "password123"})
    client.get("/logout")
    assert client.post("/login", data={"email": "a@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/login", data={"email": "a@example.com", "password": "password123"}).status_code == 302

def test_logout_blocks_dashboard(user):
    user.get("/logout")
    assert user.get("/dashboard").status_code == 302

@pytest.mark.parametrize("path", ["/api/sessions", "/api/subjects", "/api/goals", "/api/summary",
                                  "/api/chart/weekly", "/api/chart/monthly"])
def test_api_requires_authentication(client, path):
    assert client.get(path).status_code == 401


# ---------- FR2 / FR3 session logging ----------
def test_log_session_success(user):
    assert log(user, f"{TODAY}T16:00", 90).status_code == 201

@pytest.mark.parametrize("minutes", [0, -5, 721, "60", 1.5, None, True])
def test_log_session_rejects_bad_minutes(user, minutes):
    assert log(user, f"{TODAY}T16:00", minutes).status_code == 400

@pytest.mark.parametrize("when", ["", "yesterday", "2026-13-40T10:00", None])
def test_log_session_rejects_bad_time(user, when):
    assert log(user, when).status_code == 400

def test_log_session_rejects_unknown_subject(user):
    assert log(user, f"{TODAY}T10:00", sid=9999).status_code == 404

def test_edit_session(user):
    sid = log(user, f"{TODAY}T10:00", 30).get_json()["session_id"]
    r = user.put(f"/api/sessions/{sid}", json={"subject_id": first_subject(user), "start_time": f"{TODAY}T11:00", "minutes": 45})
    assert r.status_code == 200
    row = user.get("/api/sessions").get_json()[0]
    assert row["minutes"] == 45 and row["start_time"] == f"{TODAY}T11:00"

def test_delete_session(user):
    sid = log(user, f"{TODAY}T10:00").get_json()["session_id"]
    assert user.delete(f"/api/sessions/{sid}").status_code == 200
    assert user.get("/api/sessions").get_json() == []

def test_users_cannot_touch_each_others_sessions(app, user):
    sid = log(user, f"{TODAY}T10:00").get_json()["session_id"]
    other = app.test_client()
    other.post("/register", data={"email": "t2@example.com", "password": "password123"})
    assert other.delete(f"/api/sessions/{sid}").status_code == 404
    assert other.get("/api/sessions").get_json() == []

def test_filter_sessions_by_subject(user):
    sub2 = user.post("/api/subjects", json={"name": "Maths"}).get_json()["subject_id"]
    log(user, f"{TODAY}T09:00"); log(user, f"{TODAY}T10:00", sid=sub2)
    assert len(user.get(f"/api/sessions?subject_id={sub2}").get_json()) == 1

def test_sql_injection_attempt_is_harmless(user):
    r = user.post("/api/subjects", json={"name": "x'); DROP TABLE sessions;--"})
    assert r.status_code == 201
    assert log(user, f"{TODAY}T10:00").status_code == 201


# ---------- subjects ----------
def test_add_subject_and_duplicate(user):
    assert user.post("/api/subjects", json={"name": "Maths"}).status_code == 201
    assert user.post("/api/subjects", json={"name": "Maths"}).status_code == 409

@pytest.mark.parametrize("payload", [{"name": ""}, {"name": "x" * 101}, {"name": "ok", "colour": "red"}])
def test_add_subject_validation(user, payload):
    assert user.post("/api/subjects", json=payload).status_code == 400


# ---------- FR5 goals ----------
def test_set_and_update_goal(user):
    assert user.post("/api/goals", json={"period": "weekly", "target_hours": 20}).status_code == 200
    user.post("/api/goals", json={"period": "weekly", "target_hours": 25})
    assert user.get("/api/goals").get_json()["weekly"] == 25

@pytest.mark.parametrize("payload", [{"period": "daily", "target_hours": 5}, {"period": "weekly", "target_hours": 0},
                                     {"period": "weekly", "target_hours": 200}, {"period": "weekly", "target_hours": "x"}])
def test_goal_validation(user, payload):
    assert user.post("/api/goals", json=payload).status_code == 400


# ---------- FR4 / FR6 / FR7 reporting ----------
def test_weekly_chart_groups_by_day(user):
    log(user, f"{TODAY}T09:00", 60); log(user, f"{TODAY}T18:00", 30); log(user, "2026-08-31T10:00", 120)
    w = user.get(f"/api/chart/weekly?today={TODAY}").get_json()
    assert w["hours"][0] == 2.0 and w["hours"][2] == 1.5          # Mon, Wed

def test_late_night_session_stays_on_local_day(user):
    log(user, "2026-09-01T23:45", 30)                              # Tuesday 11:45 pm local
    w = user.get(f"/api/chart/weekly?today={TODAY}").get_json()
    assert w["hours"][1] == 0.5 and w["hours"][2] == 0

def test_weekly_chart_includes_daily_target(user):
    user.post("/api/goals", json={"period": "weekly", "target_hours": 14})
    assert user.get(f"/api/chart/weekly?today={TODAY}").get_json()["daily_target"] == 2.0

def test_monthly_chart_has_eight_weeks(user):
    log(user, f"{TODAY}T09:00", 60)
    m = user.get(f"/api/chart/monthly?today={TODAY}").get_json()
    assert len(m["labels"]) == 8 and m["hours"][-1] == 1.0

def test_empty_state_returns_zeroes(user):
    s = user.get(f"/api/summary?today={TODAY}").get_json()
    assert s["week_hours"] == 0 and s["streak"] == 0 and s["best_streak"] == 0

def test_summary_totals_and_average(user):
    log(user, "2026-08-31T09:00", 120); log(user, f"{TODAY}T09:00", 60)
    s = user.get(f"/api/summary?today={TODAY}").get_json()
    assert s["week_hours"] == 3.0 and s["daily_average"] == 1.0 and s["sessions_this_week"] == 2

def test_summary_goal_percentage(user):
    user.post("/api/goals", json={"period": "weekly", "target_hours": 4})
    log(user, f"{TODAY}T09:00", 60)
    assert user.get(f"/api/summary?today={TODAY}").get_json()["weekly_pct"] == 25

def d(s): return date.fromisoformat(s)

def test_streak_counts_consecutive_days():
    days = {d("2026-08-31"), d("2026-09-01"), d("2026-09-02")}
    assert analytics.streaks(days, d("2026-09-02")) == (3, 3)

def test_streak_not_broken_before_todays_session():
    days = {d("2026-08-31"), d("2026-09-01")}                      # nothing logged yet today
    assert analytics.streaks(days, d("2026-09-02")) == (2, 2)

def test_streak_resets_after_gap():
    days = {d("2026-08-27"), d("2026-08-28"), d("2026-08-29"), d("2026-09-02")}
    assert analytics.streaks(days, d("2026-09-02")) == (1, 3)

def test_streak_empty_set():
    assert analytics.streaks(set(), d("2026-09-02")) == (0, 0)


# ---------- pages ----------
def test_dashboard_page_renders_for_signed_in_user(user):
    r = user.get("/dashboard")
    assert r.status_code == 200 and b"Study" in r.data and b"weekly" in r.data
