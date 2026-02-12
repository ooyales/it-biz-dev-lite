"""
Demo Session Manager — DB-per-Session Multi-Tenancy
====================================================
Each demo session gets its own copy of the SQLite database file.
This provides complete data isolation between prospects with zero
modifications to existing SQL queries.

Flow:
    1. Prospect taps NFC → /demo?token=xxx
    2. Token validates → SessionManager copies template DB to session dir
    3. Every request: g.db_path set to session-specific DB path
    4. Prospect sees their own data, fully isolated
    5. Token expires → cleanup deletes session directory

Usage:
    from demo_sessions import SessionManager
    from demo_auth import init_demo_auth

    session_mgr = SessionManager(
        template_db="data/contacts.db",
        sessions_dir="data/sessions"
    )
    init_demo_auth(app, session_manager=session_mgr)
"""

import os
import time
import uuid
import shutil
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional


class SessionManager:
    """
    Manages demo sessions with database-per-session isolation.

    Each session gets a full copy of the template database, providing
    complete isolation. For 2-3 concurrent demo users with a ~5MB DB,
    this uses ~10-15MB of storage — trivial.
    """

    def __init__(self, template_db: str, sessions_dir: str):
        """
        Args:
            template_db: Path to the pre-seeded template database file
            sessions_dir: Directory where session databases are stored
        """
        self.template_db = Path(template_db)
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Session metadata DB (tracks active sessions)
        self.meta_db = self.sessions_dir / "sessions_meta.db"
        self._init_meta_db()

        # Cleanup expired sessions on startup
        self.cleanup_expired()

    def _init_meta_db(self):
        """Create the session metadata table."""
        conn = sqlite3.connect(str(self.meta_db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                token_hash TEXT UNIQUE,
                event_name TEXT,
                created_at REAL,
                expires_at REAL,
                db_path TEXT
            )
        """)
        conn.commit()
        conn.close()

    def get_or_create_session(
        self,
        token: str,
        event_name: str = "Demo",
        hours_remaining: float = 48,
    ) -> str:
        """
        Get existing session for this token or create a new one.
        Uses a hash of the token to look up existing sessions so the
        same token always maps to the same session/database.

        Returns:
            session_id string
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        conn = sqlite3.connect(str(self.meta_db))
        conn.row_factory = sqlite3.Row

        # Check for existing session with this token
        row = conn.execute(
            "SELECT session_id, expires_at FROM sessions WHERE token_hash = ?",
            (token_hash,)
        ).fetchone()

        if row and time.time() < row["expires_at"]:
            conn.close()
            return row["session_id"]

        # Clean up old session if expired
        if row:
            self._remove_session_files(row["session_id"])
            conn.execute("DELETE FROM sessions WHERE session_id = ?",
                         (row["session_id"],))

        # Create new session
        session_id = str(uuid.uuid4())[:12]  # Short ID for cleaner paths
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Copy template DB
        db_filename = self.template_db.name
        session_db = session_dir / db_filename
        if self.template_db.exists():
            shutil.copy2(str(self.template_db), str(session_db))
        else:
            print(f"Warning: Template DB not found at {self.template_db}")

        # Also copy any other DB files in the same directory as the template
        # (e.g., agent_logs.db might be separate but colocated)
        # We only copy the template itself — other DBs stay shared

        conn.execute("""
            INSERT INTO sessions (session_id, token_hash, event_name, created_at, expires_at, db_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            token_hash,
            event_name,
            time.time(),
            time.time() + (hours_remaining * 3600),
            str(session_db),
        ))
        conn.commit()
        conn.close()

        print(f"Created demo session {session_id} for event '{event_name}' "
              f"(expires in {hours_remaining:.0f}h)")
        return session_id

    def get_db_path(self, session_id: str) -> Optional[str]:
        """
        Get the database file path for a session.
        Returns None if session doesn't exist or is expired.
        """
        conn = sqlite3.connect(str(self.meta_db))
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT db_path, expires_at FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        conn.close()

        if not row:
            return None

        if time.time() > row["expires_at"]:
            self.cleanup_session(session_id)
            return None

        db_path = row["db_path"]
        if os.path.exists(db_path):
            return db_path

        return None

    def cleanup_session(self, session_id: str):
        """Remove a single session's data."""
        self._remove_session_files(session_id)

        conn = sqlite3.connect(str(self.meta_db))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def cleanup_expired(self):
        """Remove all expired sessions. Called on startup and periodically."""
        conn = sqlite3.connect(str(self.meta_db))
        conn.row_factory = sqlite3.Row

        expired = conn.execute(
            "SELECT session_id FROM sessions WHERE expires_at < ?",
            (time.time(),)
        ).fetchall()

        for row in expired:
            self._remove_session_files(row["session_id"])

        if expired:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?",
                         (time.time(),))
            conn.commit()
            print(f"Cleaned up {len(expired)} expired demo session(s)")

        conn.close()

    def list_active_sessions(self):
        """List all active (non-expired) sessions."""
        conn = sqlite3.connect(str(self.meta_db))
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT session_id, event_name, created_at, expires_at "
            "FROM sessions WHERE expires_at > ? ORDER BY created_at DESC",
            (time.time(),)
        ).fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def _remove_session_files(self, session_id: str):
        """Delete a session's directory and all files within it."""
        session_dir = self.sessions_dir / session_id
        if session_dir.exists() and session_dir.is_dir():
            shutil.rmtree(str(session_dir), ignore_errors=True)
