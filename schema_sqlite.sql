-- Study Sync: SQLite schema (quick demo and automated tests only)
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS subjects (
  subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  colour TEXT NOT NULL DEFAULT '#2A9D8F',
  UNIQUE (user_id, name)
);
CREATE TABLE IF NOT EXISTS sessions (
  session_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
  start_time TEXT NOT NULL,
  minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_time ON sessions (user_id, start_time);
CREATE TABLE IF NOT EXISTS goals (
  goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  period TEXT NOT NULL CHECK (period IN ('weekly','monthly')),
  target_hours REAL NOT NULL,
  UNIQUE (user_id, period)
);
