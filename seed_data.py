"""Create a demo account with realistic sample sessions:  python seed_data.py
Login: demo@studysync.test / demopass123   (pseudonymised data only)"""
import random
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash
from app import create_app
import db

random.seed(7)
app = create_app()
with app.app_context():
    db.init_db()
    db.execute("DELETE FROM users WHERE email = ?", ("demo@studysync.test",))
    uid, _ = db.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                        ("demo@studysync.test", generate_password_hash("demopass123")))
    units = [("HS3052 Capstone Project", "#2A9D8F"), ("Database Systems", "#1F3A5F"),
             ("Web Development", "#E9A23B"), ("Business Analytics", "#8E6BBF")]
    ids = [db.execute("INSERT INTO subjects (user_id, name, colour) VALUES (?, ?, ?)", (uid, n, c))[0] for n, c in units]
    today = date.today()
    for back in range(0, 56):
        d = today - timedelta(days=back)
        if d.weekday() == 6 and random.random() < .7:   # most Sundays off
            continue
        if random.random() < .12 and back > 7:
            continue
        recent = (today - d).days < 7 and d >= today - timedelta(days=today.weekday())
        if recent and random.random() < .5:      # make the current week look busy
            pass
        for _ in range(2 if recent else random.choice([1, 1, 2])):
            start = datetime(d.year, d.month, d.day, random.choice([9, 11, 14, 16, 19]), random.choice([0, 30]))
            if start > datetime.now():
                continue
            mins = random.choice([75, 90, 120, 150]) if recent else random.choice([45, 60, 75, 90, 120, 150])
            db.execute("INSERT INTO sessions (user_id, subject_id, start_time, minutes) VALUES (?, ?, ?, ?)",
                       (uid, random.choice(ids), start.strftime("%Y-%m-%d %H:%M:%S"), mins))
    db.execute("INSERT INTO goals (user_id, period, target_hours) VALUES (?, 'weekly', 20)", (uid,))
    db.execute("INSERT INTO goals (user_id, period, target_hours) VALUES (?, 'monthly', 80)", (uid,))
print("Demo data created. Login: demo@studysync.test / demopass123")
