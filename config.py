import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    DB_BACKEND = os.environ.get("DB_BACKEND", "mysql")        # "mysql" or "sqlite"
    SQLITE_PATH = os.environ.get("SQLITE_PATH", "studysync.db")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "studysync")
