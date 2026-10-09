-- Study Sync: MySQL schema (run once)
CREATE DATABASE IF NOT EXISTS studysync CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE studysync;

CREATE TABLE IF NOT EXISTS users (
  user_id       INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
  subject_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  name       VARCHAR(100) NOT NULL,
  colour     VARCHAR(7) NOT NULL DEFAULT '#2A9D8F',
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  UNIQUE KEY uq_subject (user_id, name)
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  subject_id INT NOT NULL,
  start_time DATETIME NOT NULL,          -- student's local time
  minutes    INT NOT NULL,
  FOREIGN KEY (user_id)    REFERENCES users(user_id)       ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
  INDEX idx_user_time (user_id, start_time)   -- speeds up chart aggregation
);

CREATE TABLE IF NOT EXISTS goals (
  goal_id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  period       ENUM('weekly','monthly') NOT NULL,
  target_hours DECIMAL(5,1) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  UNIQUE KEY uq_goal (user_id, period)
);
