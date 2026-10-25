import os
import sqlite3
from config import Config

try:
    import pymysql
    import pymysql.cursors
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

class Database:
    def __init__(self):
        self.engine = None
        self._detect_engine()

    def _detect_engine(self):
        if HAS_PYMYSQL and Config.MYSQL_PASSWORD != 'disable_mysql':
            try:
                # Try connecting to MySQL
                conn = pymysql.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    connect_timeout=2
                )
                with conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB}")
                conn.close()
                self.engine = 'mysql'
                print(f"[CoMitra DB] Connected to MySQL database '{Config.MYSQL_DB}' successfully.")
                return
            except Exception as e:
                # Fallback to SQLite
                print(f"[CoMitra DB] MySQL unavailable ({e}). Falling back smoothly to embedded SQLite.")
        
        self.engine = 'sqlite'
        print(f"[CoMitra DB] Using SQLite database at: {Config.SQLITE_PATH}")

    def get_connection(self):
        if self.engine == 'mysql':
            return pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        else:
            conn = sqlite3.connect(Config.SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    def format_query(self, query):
        if self.engine == 'sqlite':
            # Convert %s placeholder to ?
            return query.replace('%s', '?')
        return query

    def query(self, sql, params=None):
        conn = self.get_connection()
        formatted_sql = self.format_query(sql)
        try:
            cur = conn.cursor()
            if params:
                cur.execute(formatted_sql, params)
            else:
                cur.execute(formatted_sql)
            if self.engine == 'sqlite':
                rows = [dict(row) for row in cur.fetchall()]
            else:
                rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            conn.close()

    def query_one(self, sql, params=None):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=None):
        conn = self.get_connection()
        formatted_sql = self.format_query(sql)
        try:
            cur = conn.cursor()
            if params:
                cur.execute(formatted_sql, params)
            else:
                cur.execute(formatted_sql)
            last_id = cur.lastrowid
            if self.engine == 'sqlite':
                conn.commit()
            cur.close()
            return last_id
        finally:
            conn.close()

    def init_db(self):
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            raw_sql = f.read()

        if self.engine == 'sqlite':
            # In SQLite, replace AUTO_INCREMENT with AUTOINCREMENT
            statements = raw_sql.split(';')
            conn = self.get_connection()
            cur = conn.cursor()
            for stmt in statements:
                cleaned = stmt.strip()
                if cleaned:
                    cleaned = cleaned.replace('AUTO_INCREMENT', 'AUTOINCREMENT')
                    cur.execute(cleaned)
            conn.commit()
            conn.close()
        else:
            conn = self.get_connection()
            cur = conn.cursor()
            statements = raw_sql.split(';')
            for stmt in statements:
                cleaned = stmt.strip()
                if cleaned:
                    cur.execute(cleaned)
            conn.close()
        print(f"[CoMitra DB] Schema initialized successfully on {self.engine}.")

db = Database()
