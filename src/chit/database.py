from datetime import datetime
import sqlite3
import json

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                );
            ''')

    def create_session(self, session_id, title, model):
        with self.get_connection() as conn:
            conn.execute(
                'INSERT INTO sessions (session_id, title, model) VALUES (?, ?, ?)',
                (session_id, title, model)
            )
        return self.get_session(session_id)

    def get_session(self, session_id):
        with self.get_connection() as conn:
            session = conn.execute(
                'SELECT * FROM sessions WHERE session_id = ?',
                (session_id,)
            ).fetchone()

            if session:
                messages = conn.execute(
                    'SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp',
                    (session_id,)
                ).fetchall()

                return {
                    'session_id': session['session_id'],
                    'title': session['title'],
                    'model': session['model'],
                    'created_at': session['created_at'],
                    'messages': [dict(m) for m in messages]
                }
        return None

    def get_all_sessions(self):
        with self.get_connection() as conn:
            sessions = conn.execute(
                'SELECT s.*, COUNT(m.id) as message_count FROM sessions s ' +
                'LEFT JOIN messages m ON s.session_id = m.session_id ' +
                'GROUP BY s.session_id ' +
                'ORDER BY s.created_at DESC'
            ).fetchall()
            return [dict(s) for s in sessions]

    def add_message(self, session_id, role, content):
        with self.get_connection() as conn:
            conn.execute(
                'INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)',
                (session_id, role, content)
            )

    def update_session_title(self, session_id, title):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE sessions SET title = ? WHERE session_id = ?',
                (title, session_id)
            )

    def delete_session(self, session_id):
        with self.get_connection() as conn:
            conn.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
