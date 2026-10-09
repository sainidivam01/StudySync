"""Thin database layer. All queries are parameterised (prevents SQL injection)."""
import sqlite3
from pathlib import Path
from flask import g, current_app

ROOT = Path(__file__).parent


def _is_mysql():
    return current_app.config["DB_BACKEND"] == "mysql"


def get_conn():
    if "db" not in g:
        cfg = current_app.config
        if _is_mysql():
            import mysql.connector
            g.db = mysql.connector.connect(
                host=cfg["MYSQL_HOST"], user=cfg["MYSQL_USER"],
                password=cfg["MYSQL_PASSWORD"], database=cfg["MYSQL_DATABASE"])
        else:
            g.db = sqlite3.connect(cfg["SQLITE_PATH"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def query(sql, params=(), one=False):
    conn = get_conn()
    if _is_mysql():
        cur = conn.cursor(dictionary=True)
        cur.execute(sql.replace("?", "%s"), params)
    else:
        cur = conn.cursor()
        cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql.replace("?", "%s") if _is_mysql() else sql, params)
    conn.commit()
    last, count = cur.lastrowid, cur.rowcount
    cur.close()
    return last, count


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    """Create tables. For MySQL you can also run schema.sql directly."""
    conn = get_conn()
    if _is_mysql():
        script = (ROOT / "schema.sql").read_text()
        cur = conn.cursor()
        for stmt in [s.strip() for s in script.split(";") if s.strip()]:
            if not stmt.upper().startswith(("CREATE DATABASE", "USE")):
                cur.execute(stmt)
        conn.commit()
        cur.close()
    else:
        conn.executescript((ROOT / "schema_sqlite.sql").read_text())
        conn.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
