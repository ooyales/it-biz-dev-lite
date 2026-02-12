"""
Demo Authentication Module (Flask)
===================================
Token-based auth for frictionless demo access at government summits.
Prospects tap an NFC tag, scan a QR code, or click a link to get
instant 48-hour access — no login screen needed.

Usage:
    from demo_auth import init_demo_auth
    app = Flask(__name__)
    init_demo_auth(app)
"""

import os
import time
import hmac
import hashlib
import json
import base64
from functools import wraps
from flask import Flask, request, redirect, make_response, g, jsonify

# ─── Configuration ───

DEMO_SECRET = os.getenv("DEMO_SECRET", "change-me-to-a-real-secret-key")
DEMO_AUTH_ENABLED = os.getenv("DEMO_AUTH_ENABLED", "true").lower() == "true"

# Paths that never require authentication
PUBLIC_PATHS = {"/health", "/api/health", "/favicon.ico", "/demo", "/demo-expired"}
PUBLIC_PREFIXES = ("/static/", "/_next/", "/assets/")


# ─── Token Creation & Verification ───

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def create_demo_token(event_name="Demo", hours=48, issued_to="demo_visitor"):
    """Create a signed, time-limited demo access token."""
    payload = {
        "event": event_name,
        "issued_to": issued_to,
        "iat": int(time.time()),
        "exp": int(time.time()) + (hours * 3600),
    }
    payload_b64 = _b64url_encode(json.dumps(payload).encode())
    signature = hmac.new(
        DEMO_SECRET.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_demo_token(token):
    """
    Verify token signature and expiry.
    Returns payload dict on success, None on failure.
    """
    try:
        payload_b64, signature = token.rsplit(".", 1)
    except (ValueError, AttributeError):
        return None

    expected_sig = hmac.new(
        DEMO_SECRET.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, Exception):
        return None

    if time.time() > payload.get("exp", 0):
        return None  # Expired

    return payload


# ─── Flask Integration ───

DEMO_EXPIRED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Demo Access Expired</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
            max-width: 600px;
            margin: 100px auto;
            text-align: center;
            color: #333;
            padding: 20px;
        }
        h1 { color: #1a1a2e; margin-bottom: 16px; }
        p { color: #666; line-height: 1.6; }
        .icon { font-size: 48px; margin-bottom: 20px; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="icon">🔒</div>
    <h1>Demo Access Expired</h1>
    <p>Your temporary demo access has expired or the link is invalid.</p>
    <p>Please contact us for a new demo link.</p>
    <p style="margin-top: 40px;">
        <a href="mailto:demo@example.com">Request New Access</a>
    </p>
</body>
</html>
"""

DEMO_MISSING_TOKEN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Demo Access Required</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
            max-width: 600px;
            margin: 100px auto;
            text-align: center;
            color: #333;
            padding: 20px;
        }
        h1 { color: #1a1a2e; }
        p { color: #666; line-height: 1.6; }
        .icon { font-size: 48px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="icon">🔗</div>
    <h1>Demo Access Required</h1>
    <p>A valid demo link is required to access this application.</p>
    <p>Please use the link provided at the event or contact us.</p>
</body>
</html>
"""


def init_demo_auth(app, session_manager=None):
    """
    Initialize demo authentication on a Flask app.

    Args:
        app: Flask application instance
        session_manager: Optional SessionManager for multi-tenant DB isolation.
                         If provided, creates a session DB on first token use
                         and sets g.demo_session_id and g.db_path before each request.
    """

    @app.route("/demo")
    def demo_entry():
        token = request.args.get("token")
        if not token:
            return DEMO_MISSING_TOKEN_HTML, 400

        payload = verify_demo_token(token)
        if payload is None:
            return redirect("/demo-expired")

        # Create or retrieve demo session
        session_id = None
        if session_manager:
            session_id = session_manager.get_or_create_session(
                token=token,
                event_name=payload.get("event", "Demo"),
                hours_remaining=max(0, (payload["exp"] - int(time.time())) / 3600),
            )

        # Set cookie and redirect to app
        response = make_response(redirect("/"))
        max_age = max(0, payload["exp"] - int(time.time()))
        response.set_cookie(
            "demo_session",
            value=token,
            max_age=max_age,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
        )
        if session_id:
            response.set_cookie(
                "demo_session_id",
                value=session_id,
                max_age=max_age,
                httponly=True,
                secure=request.is_secure,
                samesite="Lax",
            )
        return response

    @app.route("/demo-expired")
    def demo_expired():
        return DEMO_EXPIRED_HTML, 403

    @app.before_request
    def check_demo_auth():
        # Skip if auth disabled
        if not DEMO_AUTH_ENABLED:
            return

        path = request.path

        # Skip public paths
        if path in PUBLIC_PATHS:
            return
        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return

        # Check session cookie
        session_token = request.cookies.get("demo_session")
        if session_token:
            payload = verify_demo_token(session_token)
            if payload:
                g.demo_payload = payload
                # Set session-specific DB path if session manager is available
                if session_manager:
                    session_id = request.cookies.get("demo_session_id")
                    if session_id:
                        db_path = session_manager.get_db_path(session_id)
                        if db_path:
                            g.demo_session_id = session_id
                            g.db_path = db_path
                            return
                else:
                    return  # No session manager, just validate token

        # No valid session — redirect to expired page
        return redirect("/demo-expired")
