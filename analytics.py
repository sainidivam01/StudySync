"""Reporting module: turns stored sessions into chart series and summary figures."""
from datetime import date, timedelta
import db


def week_start(d):
    return d - timedelta(days=d.weekday())          # Monday


def daily_minutes(user_id, start, end, subject_id=None):
    """Study minutes between two dates, optionally for one subject."""
    sql = (
        "SELECT DATE(start_time) AS d, SUM(minutes) AS m FROM sessions "
        "WHERE user_id = ? AND DATE(start_time) BETWEEN ? AND ?"
    )

    params = [user_id, start.isoformat(), end.isoformat()]

    if subject_id:
        sql += " AND subject_id = ?"
        params.append(subject_id)

    sql += " GROUP BY DATE(start_time)"

    rows = db.query(sql, tuple(params))

    return {
        date.fromisoformat(str(r["d"])): int(r["m"])
        for r in rows
    }

def streaks(days, today):
    """Current streak counts completed days; today only counts once a session is logged."""
    cur, d = 0, (today if today in days else today - timedelta(days=1))
    while d in days:
        cur += 1
        d -= timedelta(days=1)
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    return cur, best


def get_goal(user_id, period):
    row = db.query("SELECT target_hours FROM goals WHERE user_id = ? AND period = ?",
                   (user_id, period), one=True)
    return float(row["target_hours"]) if row else None

def weekly_chart(user_id, today, subject_id=None):
    start = week_start(today)

    mins = daily_minutes(
        user_id,
        start,
        start + timedelta(days=6),
        subject_id
    )

    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    hours = [
        round(
            mins.get(start + timedelta(days=i), 0) / 60,
            2
        )
        for i in range(7)
    ]

    weekly = get_goal(user_id, "weekly")

    return {
        "labels": labels,
        "hours": hours,
        "daily_target": round(weekly / 7, 2) if weekly and not subject_id else None
    }
def monthly_chart(user_id, today, weeks=8, subject_id=None):
    first = week_start(today) - timedelta(weeks=weeks - 1)

    mins = daily_minutes(
        user_id,
        first,
        today,
        subject_id
    )

    labels = []
    hours = []

    for w in range(weeks):
        ws = first + timedelta(weeks=w)

        total = sum(
            mins.get(ws + timedelta(days=i), 0)
            for i in range(7)
        )

        labels.append(ws.strftime("%d %b").lstrip("0"))
        hours.append(round(total / 60, 1))

    return {
        "labels": labels,
        "hours": hours
    }

def summary(user_id, today, subject_id=None):
    ws = week_start(today)

    week_mins = daily_minutes(
        user_id,
        ws,
        today,
        subject_id
    )

    total_week = sum(week_mins.values()) / 60
    days_elapsed = today.weekday() + 1

    month_start = today.replace(day=1)

    month_total = sum(
        daily_minutes(
            user_id,
            month_start,
            today,
            subject_id
        ).values()
    ) / 60

    sql = "SELECT DISTINCT DATE(start_time) AS d FROM sessions WHERE user_id = ?"
    params = [user_id]

    if subject_id:
        sql += " AND subject_id = ?"
        params.append(subject_id)

    all_days = {
        date.fromisoformat(str(r["d"]))
        for r in db.query(sql, tuple(params))
    }

    cur, best = streaks(all_days, today)

    sql = (
        "SELECT COUNT(*) AS c FROM sessions "
        "WHERE user_id = ? "
        "AND DATE(start_time) BETWEEN ? AND ?"
    )

    params = [
        user_id,
        ws.isoformat(),
        today.isoformat()
    ]

    if subject_id:
        sql += " AND subject_id = ?"
        params.append(subject_id)

    count = db.query(
        sql,
        tuple(params),
        one=True
    )["c"]

    if subject_id:
        units = 1 if count else 0
    else:
        units = db.query(
            "SELECT COUNT(DISTINCT subject_id) AS c FROM sessions "
            "WHERE user_id = ? "
            "AND DATE(start_time) BETWEEN ? AND ?",
            (
                user_id,
                ws.isoformat(),
                today.isoformat()
            ),
            one=True
        )["c"]

    wg = get_goal(user_id, "weekly")
    mg = get_goal(user_id, "monthly")

    return {
        "week_hours": round(total_week, 1),
        "daily_average": round(total_week / days_elapsed, 1),
        "streak": cur,
        "best_streak": best,
        "sessions_this_week": count,
        "units_this_week": units,

        "weekly_goal": None if subject_id else wg,
        "monthly_goal": None if subject_id else mg,

        "weekly_pct": None if subject_id else (
            round(min(100, total_week / wg * 100))
            if wg else None
        ),

        "month_hours": round(month_total, 1),

        "monthly_pct": None if subject_id else (
            round(min(100, month_total / mg * 100))
            if mg else None
        ),
    }