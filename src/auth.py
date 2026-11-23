"""Google OAuth 2.0 + Personal Onboarding + Multi-User Authentication for MoneyLens AI.

Supports:
1. Official Google OAuth 2.0 Authorization Code Flow (when GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET are set in .env).
2. Instant Local Google Sign-In (works immediately on localhost without requiring Cloud Console setup) where every
   distinct Google email creates its own isolated account, asks for personal onboarding info on first login, and
   displays that user's own name, avatar, budget, and personal Webhook token.
3. Classic Email & Password accounts (PBKDF2-HMAC-SHA256, 200,000 iterations) as an optional secondary sign-in method.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from src.data_processing import DEFAULT_DB_PATH, init_db, seed_user_demo_transactions

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

USER_SELECT_COLS = """
    id, email, full_name, plan, monthly_budget,
    auth_provider, google_sub, avatar_url, occupation,
    monthly_income, financial_goal, preferred_banks,
    onboarding_completed, webhook_token, webhook_secret, created_at
"""


def _row_to_user(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": int(row[0]),
        "email": str(row[1]),
        "full_name": str(row[2] or ""),
        "plan": str(row[3] or "Personal"),
        "monthly_budget": float(row[4] or 8_000_000),
        "auth_provider": str(row[5] or "google"),
        "google_sub": str(row[6] or ""),
        "avatar_url": str(row[7] or ""),
        "occupation": str(row[8] or ""),
        "monthly_income": float(row[9] or 0),
        "financial_goal": str(row[10] or ""),
        "preferred_banks": [b.strip() for b in str(row[11] or "").split(",") if b.strip()],
        "onboarding_completed": bool(int(row[12] or 0)),
        "webhook_token": str(row[13] or ""),
        "webhook_secret": str(row[14] or ""),
        "created_at": str(row[15] or ""),
    }


def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return dk.hex()


def _new_webhook_token() -> str:
    return f"ml_{secrets.token_urlsafe(16)}"


# ---------------------------------------------------------------------------
# Google OAuth 2.0 Helpers (Live Production Flow when configured in .env)
# ---------------------------------------------------------------------------
def is_google_oauth_configured() -> bool:
    """Return True when real Google Cloud OAuth 2.0 credentials are set in environment."""
    return bool(os.getenv("GOOGLE_CLIENT_ID", "").strip() and os.getenv("GOOGLE_CLIENT_SECRET", "").strip())


def get_google_redirect_uri() -> str:
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501").strip()


def get_google_oauth_url(state: str) -> str:
    """Build official Google OAuth 2.0 consent URL."""
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "redirect_uri": get_google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def exchange_google_oauth_code(code: str) -> tuple[dict[str, str] | None, str | None]:
    """Exchange Google OAuth authorization code for verified user email, name, sub & picture."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None, "Chưa cấu hình GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET."

    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": get_google_redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=12,
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None, f"Google OAuth token error: {token_data.get('error_description') or token_data.get('error') or 'unknown'}"

        info_resp = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info = info_resp.json()
        email = str(info.get("email", "")).strip().lower()
        if not email:
            return None, "Không lấy được địa chỉ email từ Google."
        return {
            "email": email,
            "full_name": str(info.get("name", "")).strip(),
            "avatar_url": str(info.get("picture", "")).strip(),
            "google_sub": str(info.get("sub", "")).strip(),
        }, None
    except Exception as exc:
        return None, f"Lỗi kết nối Google OAuth: {exc}"


# ---------------------------------------------------------------------------
# User Lookups & Google Sign-In
# ---------------------------------------------------------------------------
def get_user_by_id(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(f"SELECT {USER_SELECT_COLS} FROM users WHERE id = ?", (int(user_id),)).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_webhook_token(webhook_token: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Resolve user account owning a personal auto-sync webhook token."""
    init_db(db_path)
    tok = str(webhook_token or "").strip()
    if not tok:
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"SELECT {USER_SELECT_COLS} FROM users WHERE webhook_token = ? LIMIT 1",
            (tok,),
        ).fetchone()
    return _row_to_user(row) if row else None


def create_user_session(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> str:
    """Create a persistent SQLite login session token so F5 / revisits keep the user logged in."""
    init_db(db_path)
    token = f"mls_{secrets.token_urlsafe(24)}"
    now_iso = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO user_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, int(user_id), now_iso),
        )
        conn.commit()
    return token


def get_user_by_session_token(token: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Restore signed-in user from a persisted session token in SQLite."""
    tok = str(token or "").strip()
    if not tok:
        return None
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT {USER_SELECT_COLS}
            FROM users
            WHERE id = (SELECT user_id FROM user_sessions WHERE token = ? LIMIT 1)
            LIMIT 1
            """,
            (tok,),
        ).fetchone()
    return _row_to_user(row) if row else None


def delete_user_session(token: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Revoke a persisted session token on Sign Out."""
    tok = str(token or "").strip()
    if not tok:
        return
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM user_sessions WHERE token = ?", (tok,))
        conn.commit()


def list_google_accounts(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Return previously onboarded user accounts (excluding legacy seeded demo email)."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT {USER_SELECT_COLS}
            FROM users
            WHERE email != 'demo@moneylens.vn' AND onboarding_completed = 1
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()
    return [_row_to_user(r) for r in rows]


def sign_in_with_google_profile(
    email: str,
    full_name: str = "",
    avatar_url: str = "",
    google_sub: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, str | None]:
    """Sign in or create a distinct per-Google-account user.

    Returning Google accounts always keep their saved profile & `onboarding_completed = True`
    so users are never asked to re-enter their name on subsequent sign-ins.
    """
    init_db(db_path)
    email_clean = str(email).strip().lower()
    if not EMAIL_RE.match(email_clean):
        return None, "Địa chỉ email Google không hợp lệ (VD: tenban@gmail.com)."

    with sqlite3.connect(db_path) as conn:
        existing = None
        if google_sub and str(google_sub).strip():
            existing = conn.execute(
                f"SELECT {USER_SELECT_COLS} FROM users WHERE google_sub = ? LIMIT 1",
                (str(google_sub).strip(),),
            ).fetchone()
        if existing is None:
            existing = conn.execute(
                f"SELECT {USER_SELECT_COLS} FROM users WHERE LOWER(TRIM(email)) = ? LIMIT 1",
                (email_clean,),
            ).fetchone()
        if existing:
            user = _row_to_user(existing)
            tok = user["webhook_token"] or _new_webhook_token()
            new_avatar = avatar_url or user["avatar_url"]
            new_sub = google_sub or user["google_sub"]
            has_saved_name = len(str(user.get("full_name", "")).strip()) >= 2
            done_flag = 1 if (user["onboarding_completed"] or has_saved_name) else 0
            conn.execute(
                """
                UPDATE users
                SET auth_provider = 'google',
                    avatar_url = ?,
                    google_sub = ?,
                    webhook_token = ?,
                    onboarding_completed = ?
                WHERE id = ?
                """,
                (new_avatar, new_sub, tok, done_flag, user["id"]),
            )
            conn.commit()
            refreshed = conn.execute(
                f"SELECT {USER_SELECT_COLS} FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()
            return _row_to_user(refreshed), None

        now_iso = datetime.now().isoformat(timespec="seconds")
        tok = _new_webhook_token()
        cur = conn.execute(
            """
            INSERT INTO users
            (email, full_name, password_hash, salt, plan, monthly_budget,
             auth_provider, google_sub, avatar_url, occupation, monthly_income,
             financial_goal, preferred_banks, onboarding_completed, webhook_token, webhook_secret, created_at)
            VALUES (?, ?, '', '', 'Google Account', 8000000, 'google', ?, ?, '', 0, '', '', 0, ?, '', ?)
            """,
            (email_clean, str(full_name).strip(), str(google_sub).strip(), str(avatar_url).strip(), tok, now_iso),
        )
        conn.commit()
        uid = int(cur.lastrowid)
        row = conn.execute(f"SELECT {USER_SELECT_COLS} FROM users WHERE id = ?", (uid,)).fetchone()
    return _row_to_user(row), None


def complete_user_onboarding(
    user_id: int,
    full_name: str,
    occupation: str,
    monthly_income: float,
    monthly_budget: float,
    financial_goal: str,
    preferred_banks: list[str] | None = None,
    seed_sample_data: bool = False,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, str | None]:
    """Save mandatory personal onboarding details and unlock the user's personalized workspace."""
    init_db(db_path)
    name_clean = str(full_name).strip()
    if len(name_clean) < 2:
        return None, "Vui lòng nhập Họ và tên đầy đủ (tối thiểu 2 ký tự)."

    banks_csv = ", ".join(b.strip() for b in (preferred_banks or []) if b.strip())
    budget_val = max(float(monthly_budget), 500_000.0)
    income_val = max(float(monthly_income), 0.0)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE users
            SET full_name = ?,
                occupation = ?,
                monthly_income = ?,
                monthly_budget = ?,
                financial_goal = ?,
                preferred_banks = ?,
                plan = ?,
                onboarding_completed = 1
            WHERE id = ?
            """,
            (
                name_clean,
                str(occupation).strip(),
                income_val,
                budget_val,
                str(financial_goal).strip(),
                banks_csv,
                str(occupation).strip() or "Personal",
                int(user_id),
            ),
        )
        conn.commit()
        tx_cnt = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()[0]

    if seed_sample_data and int(tx_cnt or 0) == 0:
        seed_user_demo_transactions(int(user_id), db_path=db_path)

    return get_user_by_id(int(user_id), db_path=db_path), None


def update_user_profile(
    user_id: int,
    full_name: str,
    occupation: str,
    monthly_income: float,
    monthly_budget: float,
    financial_goal: str,
    preferred_banks: list[str] | None = None,
    webhook_secret: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, str | None]:
    """Allow an onboarded user to update their personal profile & webhook secret anytime."""
    init_db(db_path)
    name_clean = str(full_name).strip()
    if len(name_clean) < 2:
        return None, "Họ và tên cần tối thiểu 2 ký tự."
    banks_csv = ", ".join(b.strip() for b in (preferred_banks or []) if b.strip())

    with sqlite3.connect(db_path) as conn:
        if webhook_secret is not None:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, occupation = ?, monthly_income = ?, monthly_budget = ?,
                    financial_goal = ?, preferred_banks = ?, plan = ?, webhook_secret = ?
                WHERE id = ?
                """,
                (
                    name_clean,
                    str(occupation).strip(),
                    max(float(monthly_income), 0.0),
                    max(float(monthly_budget), 500_000.0),
                    str(financial_goal).strip(),
                    banks_csv,
                    str(occupation).strip() or "Personal",
                    str(webhook_secret).strip(),
                    int(user_id),
                ),
            )
        else:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, occupation = ?, monthly_income = ?, monthly_budget = ?,
                    financial_goal = ?, preferred_banks = ?, plan = ?
                WHERE id = ?
                """,
                (
                    name_clean,
                    str(occupation).strip(),
                    max(float(monthly_income), 0.0),
                    max(float(monthly_budget), 500_000.0),
                    str(financial_goal).strip(),
                    banks_csv,
                    str(occupation).strip() or "Personal",
                    int(user_id),
                ),
            )
        conn.commit()
    return get_user_by_id(int(user_id), db_path=db_path), None


def regenerate_webhook_token(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Rotate the user's personal auto-sync webhook token."""
    init_db(db_path)
    new_tok = _new_webhook_token()
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE users SET webhook_token = ? WHERE id = ?", (new_tok, int(user_id)))
        conn.commit()
    return get_user_by_id(int(user_id), db_path=db_path)


# ---------------------------------------------------------------------------
# Classic Email / Password Registration & Login (Optional Secondary Channel)
# ---------------------------------------------------------------------------
def register_user(
    full_name: str,
    email: str,
    password: str,
    seed_sample_data: bool = False,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, str | None]:
    """Register a new email/password account (enters personal onboarding on first sign-in)."""
    init_db(db_path)
    name_clean = str(full_name).strip()
    email_clean = str(email).strip().lower()

    if not EMAIL_RE.match(email_clean):
        return None, "Email không đúng định dạng (VD: ban@gmail.com)."
    if len(password) < 6:
        return None, "Mật khẩu cần tối thiểu 6 ký tự."

    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    now_iso = datetime.now().isoformat(timespec="seconds")
    tok = _new_webhook_token()

    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO users
                (email, full_name, password_hash, salt, plan, monthly_budget,
                 auth_provider, onboarding_completed, webhook_token, created_at)
                VALUES (?, ?, ?, ?, 'Standard', 8000000, 'password', 0, ?, ?)
                """,
                (email_clean, name_clean, pw_hash, salt, tok, now_iso),
            )
            conn.commit()
            uid = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return None, "Email này đã được đăng ký. Vui lòng đăng nhập hoặc dùng tài khoản Google."

    if seed_sample_data:
        seed_user_demo_transactions(uid, db_path=db_path)

    return get_user_by_id(uid, db_path=db_path), None


def authenticate_user(
    email: str,
    password: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, str | None]:
    """Verify email/password credentials using constant-time HMAC comparison."""
    init_db(db_path)
    email_clean = str(email).strip().lower()
    if not email_clean or not password:
        return None, "Vui lòng nhập đầy đủ email và mật khẩu."

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, password_hash, salt, auth_provider FROM users WHERE email = ?",
            (email_clean,),
        ).fetchone()
    if not row:
        return None, "Email chưa tồn tại trong hệ thống."

    uid, stored_hash, salt, provider = row
    if not stored_hash or not salt:
        return None, "Tài khoản này đăng nhập bằng Google. Vui lòng bấm 'Tiếp tục với Google'."
    calc_hash = _hash_password(password, salt)
    if not hmac.compare_digest(stored_hash, calc_hash):
        return None, "Mật khẩu không chính xác."

    return get_user_by_id(int(uid), db_path=db_path), None


def update_user_budget(user_id: int, monthly_budget: float, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Persist updated monthly budget target for the logged-in user."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE users SET monthly_budget = ? WHERE id = ?",
            (float(monthly_budget), int(user_id)),
        )
        conn.commit()
