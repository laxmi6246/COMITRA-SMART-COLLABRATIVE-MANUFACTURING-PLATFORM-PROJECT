import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'comitra-secret-key-2026-production')
    
    # MySQL Database Config (with fallback to SQLite)
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'comitra_db')
    
    # SQLite Fallback File
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'comitra.db')
