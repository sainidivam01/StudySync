# Study Sync: Digital Study Habit Tracker
HS3052 Capstone Project (Design). Stack: HTML/CSS/JavaScript + Chart.js, Python Flask, MySQL.

## Project structure
| File / folder | Purpose |
|---|---|
| `app.py` | Flask app: pages, authentication, REST API (sessions, subjects, goals, charts, summary) |
| `analytics.py` | Reporting module: SQL aggregation, streaks, chart series, summary figures |
| `db.py`, `config.py` | Database layer (parameterised queries) and settings |
| `schema.sql` | MySQL schema (users, subjects, sessions, goals + index) |
| `schema_sqlite.sql` | Same schema for SQLite (quick demo / tests only) |
| `templates/`, `static/` | Pages, CSS, JavaScript, local copy of Chart.js |
| `seed_data.py` | Creates a demo user with sample data |
| `tests/` | Automated tests (pytest) |

## Quick start (no MySQL needed, SQLite demo)
```bash
pip install -r requirements.txt
export DB_BACKEND=sqlite            # Windows PowerShell:  $env:DB_BACKEND="sqlite"
python seed_data.py                 # demo login: demo@studysync.test / demopass123
flask --app app run                 # open http://127.0.0.1:5000
```

## Running with MySQL (as described in the report)
```bash
mysql -u root -p < schema.sql
export MYSQL_USER=root MYSQL_PASSWORD=yourpassword MYSQL_DATABASE=studysync
export SECRET_KEY=some-long-random-string
flask --app app run
```
(`DB_BACKEND` defaults to `mysql`.)

## Tests
```bash
python -m pytest -v
```
Tests use a temporary SQLite database and cover authentication, validation, CRUD,
per-user data isolation, SQL-injection input, chart grouping, time-zone/late-night
sessions, streak logic, goals and summaries.

## Notes
- Passwords are hashed (Werkzeug). All SQL uses bound parameters. Sessions expire after 30 min of inactivity.
- Session times are stored in the student's local time; the browser sends its own calendar day, which avoids server time-zone errors.
- Use pseudonymised data only when testing (e.g. T1 to T4).
