"""Data Processing & Multi-User SQLite Persistence Layer (MoneyLens AI).

Stores per-user transactions (supporting Quick Text, Bill OCR, Bank Transfer Sync, and Demo seed),
user accounts, transfer memos, AI notes, and budget preferences in `data/moneylens.db`.
"""

from __future__ import annotations

import hashlib
import io
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["date", "description", "amount", "type", "category"]
CANONICAL_EXPENSE_CATEGORIES = ["Food", "Shopping", "Transport", "Bills", "Entertainment", "Other"]

CATEGORY_ALIASES: dict[str, str] = {
    "food": "Food",
    "ăn uống": "Food",
    "an uong": "Food",
    "dining": "Food",
    "coffee": "Food",
    "shopping": "Shopping",
    "mua sắm": "Shopping",
    "mua sam": "Shopping",
    "transport": "Transport",
    "di chuyển": "Transport",
    "di chuyen": "Transport",
    "travel": "Transport",
    "bills": "Bills",
    "hóa đơn": "Bills",
    "hoa don": "Bills",
    "utilities": "Bills",
    "rent": "Bills",
    "entertainment": "Entertainment",
    "giải trí": "Entertainment",
    "giai tri": "Entertainment",
    "subscription": "Entertainment",
    "other": "Other",
    "khác": "Other",
    "khac": "Other",
    "education": "Other",
    "health": "Other",
    "income": "Income",
    "thu nhập": "Income",
    "thu nhap": "Income",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "moneylens.db"
SEED_DATA_PATH = PROJECT_ROOT / "data" / "sample_transactions.csv"


def normalize_category_value(raw_cat: Any, tx_type: str) -> str:
    """Normalize a raw category cell to a canonical group or empty string."""
    if tx_type == "income":
        return "Income"
    if raw_cat is None or (isinstance(raw_cat, float) and np.isnan(raw_cat)):
        return ""
    cleaned = str(raw_cat).strip()
    if not cleaned or cleaned.lower() in {"nan", "none", "null", "n/a", "-"}:
        return ""
    return CATEGORY_ALIASES.get(
        cleaned.lower(),
        cleaned if cleaned in CANONICAL_EXPENSE_CATEGORIES else "Other",
    )


def parse_csv_source(file_source: Any) -> tuple[pd.DataFrame | None, str | None]:
    """Read internal seed CSV or DataFrame safely across encodings."""
    try:
        if isinstance(file_source, pd.DataFrame):
            return file_source.copy(), None
        if isinstance(file_source, (str, Path)):
            raw_bytes = Path(file_source).read_bytes()
        elif hasattr(file_source, "getvalue"):
            raw_bytes = file_source.getvalue()
        else:
            raw_bytes = file_source.read()

        if isinstance(raw_bytes, bytes):
            decoded = None
            for enc in ("utf-8-sig", "utf-8", "cp1258", "latin1"):
                try:
                    decoded = raw_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                return None, "Không thể giải mã dữ liệu."
            return pd.read_csv(io.StringIO(decoded), dtype={"category": str}), None
        return pd.read_csv(io.StringIO(str(raw_bytes)), dtype={"category": str}), None
    except Exception as exc:
        return None, f"Lỗi đọc dữ liệu: {exc}"


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean a transaction DataFrame adhering strictly to the 5-column core schema."""
    cleaned = df.copy()
    cleaned.columns = [str(c).strip().lower() for c in cleaned.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in cleaned.columns]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {', '.join(missing)}.")

    extra_cols = [c for c in ("id", "source_type", "transfer_memo", "ai_note", "category_confidence") if c in cleaned.columns]
    cleaned = cleaned[REQUIRED_COLUMNS + extra_cols].copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned["description"] = cleaned["description"].fillna("").astype(str).str.strip()

    amt_str = (
        cleaned["amount"]
        .astype(str)
        .str.replace("₫", "", regex=False)
        .str.replace("vnd", "", case=False, regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    cleaned["amount"] = pd.to_numeric(amt_str, errors="coerce")
    cleaned["type"] = cleaned["type"].fillna("").astype(str).str.strip().str.lower()

    valid_mask = (
        cleaned["date"].notna()
        & cleaned["amount"].notna()
        & (cleaned["amount"] != 0)
        & cleaned["type"].isin(["income", "expense"])
        & (cleaned["description"] != "")
    )
    dropped_rows = int((~valid_mask).sum())
    cleaned = cleaned.loc[valid_mask].copy()
    if cleaned.empty:
        raise ValueError("Không có giao dịch hợp lệ.")

    neg_count = int((cleaned["amount"] < 0).sum())
    cleaned["amount"] = cleaned["amount"].abs().astype(float)
    cleaned["category"] = [
        normalize_category_value(cat, tx_type)
        for cat, tx_type in zip(cleaned["category"], cleaned["type"])
    ]
    cleaned["is_auto_categorized"] = cleaned["category"] == ""
    if "source_type" not in cleaned.columns:
        cleaned["source_type"] = "bank_sync"
    if "transfer_memo" not in cleaned.columns:
        cleaned["transfer_memo"] = ""
    if "ai_note" not in cleaned.columns:
        cleaned["ai_note"] = ""

    cleaned["signed_amount"] = np.where(cleaned["type"] == "income", cleaned["amount"], -cleaned["amount"])
    cleaned["year_month"] = cleaned["date"].dt.strftime("%Y-%m")
    cleaned = cleaned.sort_values("date").reset_index(drop=True)
    cleaned.attrs["dropped_rows"] = dropped_rows
    cleaned.attrs["normalized_negative_rows"] = neg_count
    return cleaned


# ---------------------------------------------------------------------------
# Multi-User SQLite Persistence (`data/moneylens.db`)
# ---------------------------------------------------------------------------
def _ensure_column(conn: sqlite3.Connection, table: str, col_name: str, col_def: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if col_name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")


def init_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    """Initialize/migrate SQLite tables for multi-user Google/Email accounts, transactions & live webhooks."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                salt TEXT NOT NULL DEFAULT '',
                plan TEXT NOT NULL DEFAULT 'Personal',
                monthly_budget REAL NOT NULL DEFAULT 8000000,
                auth_provider TEXT NOT NULL DEFAULT 'google',
                google_sub TEXT NOT NULL DEFAULT '',
                avatar_url TEXT NOT NULL DEFAULT '',
                occupation TEXT NOT NULL DEFAULT '',
                monthly_income REAL NOT NULL DEFAULT 0,
                financial_goal TEXT NOT NULL DEFAULT '',
                preferred_banks TEXT NOT NULL DEFAULT '',
                onboarding_completed INTEGER NOT NULL DEFAULT 0,
                webhook_token TEXT NOT NULL DEFAULT '',
                webhook_secret TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                is_auto_categorized INTEGER NOT NULL DEFAULT 0,
                category_confidence REAL NOT NULL DEFAULT 1.0,
                source_type TEXT NOT NULL DEFAULT 'bank_sync',
                transfer_memo TEXT NOT NULL DEFAULT '',
                ai_note TEXT NOT NULL DEFAULT '',
                external_ref TEXT NOT NULL DEFAULT '',
                source_name TEXT NOT NULL DEFAULT 'moneylens',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                tx_id INTEGER,
                summary TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                tx_type TEXT NOT NULL DEFAULT 'expense',
                received_at TEXT NOT NULL
            )
            """
        )

        # Safe migrations for pre-existing databases
        _ensure_column(conn, "users", "auth_provider", "TEXT NOT NULL DEFAULT 'password'")
        _ensure_column(conn, "users", "google_sub", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "avatar_url", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "occupation", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "monthly_income", "REAL NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "financial_goal", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "preferred_banks", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "onboarding_completed", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "users", "webhook_token", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "users", "webhook_secret", "TEXT NOT NULL DEFAULT ''")

        _ensure_column(conn, "transactions", "user_id", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "transactions", "source_type", "TEXT NOT NULL DEFAULT 'bank_sync'")
        _ensure_column(conn, "transactions", "transfer_memo", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "transactions", "ai_note", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "transactions", "external_ref", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "transactions", "tx_timestamp", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "transactions", "counterparty", "TEXT NOT NULL DEFAULT ''")

        # Partial unique index: enforces atomicity ONLY on non-empty sync keys (manual entries with '' are never blocked!)
        conn.execute(
            """
            DELETE FROM transactions
            WHERE external_ref != ''
              AND id NOT IN (
                  SELECT MIN(id) FROM transactions WHERE external_ref != '' GROUP BY user_id, external_ref
              )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_user_extref_unique
            ON transactions (user_id, external_ref)
            WHERE external_ref != ''
            """
        )

        # Backfill missing webhook tokens for any existing users
        missing_tok_rows = conn.execute(
            "SELECT id FROM users WHERE webhook_token IS NULL OR webhook_token = ''"
        ).fetchall()
        for (uid,) in missing_tok_rows:
            tok = f"ml_{secrets.token_urlsafe(16)}"
            conn.execute("UPDATE users SET webhook_token = ? WHERE id = ?", (tok, int(uid)))

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fixed_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL DEFAULT 'Bills',
                due_day INTEGER NOT NULL DEFAULT 1,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_sync_configs (
                user_id INTEGER PRIMARY KEY,
                email_address TEXT NOT NULL DEFAULT '',
                app_password_enc TEXT NOT NULL DEFAULT '',
                imap_host TEXT NOT NULL DEFAULT 'imap.gmail.com',
                imap_port INTEGER NOT NULL DEFAULT 993,
                enabled INTEGER NOT NULL DEFAULT 0,
                last_uid INTEGER NOT NULL DEFAULT 0,
                last_checked_at TEXT NOT NULL DEFAULT '',
                last_status TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                synced_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    return db_path


def save_transactions_to_db(
    df: pd.DataFrame,
    source_name: str = "moneylens",
    user_id: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Replace active user's transactions snapshot in SQLite."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    rows = []
    for _, r in df.iterrows():
        dt_str = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
        rows.append(
            (
                int(user_id),
                dt_str,
                str(r["description"]),
                float(r["amount"]),
                str(r["type"]),
                str(r["category"]),
                1 if bool(r.get("is_auto_categorized", False)) else 0,
                float(r.get("category_confidence", 1.0)),
                str(r.get("source_type", "bank_sync")),
                str(r.get("transfer_memo", "")),
                str(r.get("ai_note", "")),
                source_name,
                now_iso,
            )
        )

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (int(user_id),))
        conn.executemany(
            """
            INSERT INTO transactions
            (user_id, date, description, amount, type, category, is_auto_categorized,
             category_confidence, source_type, transfer_memo, ai_note, source_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    return len(rows)


def _norm_dedup_text(val: Any) -> str:
    return re.sub(r"\s+", " ", str(val or "").strip().lower())


def build_transaction_unique_key(
    user_id: int,
    date_str: str,
    amount: float,
    tx_type: str,
    transfer_memo: str = "",
    tx_timestamp: str = "",
    counterparty: str = "",
    reference_code: str = "",
    provider: str = "",
) -> str:
    """Build canonical deduplication key following strict 2-tier priority:

    Priority 1: Official Transaction ID / Reference Code (`ref:<provider>:<ref_code>`).
    Priority 2: Composite SHA-256 fingerprint (`fp:<sha256>`) over ALL 5 fields:
        exact timestamp + direction (IN/OUT) + amount + transfer memo + counterparty/account.
    If ANY single field differs, a distinct key is produced so valid new transactions are NEVER skipped.
    """
    ref_raw = re.sub(r"\s+", "", str(reference_code or "").strip()).upper()
    if ref_raw and len(ref_raw) >= 4:
        prov_clean = re.sub(r"[^a-z0-9]+", "_", str(provider or "tx").strip().lower()).strip("_") or "tx"
        return f"ref:{prov_clean}:{ref_raw[:96]}"

    ts_clean = str(tx_timestamp or "").strip()
    if not ts_clean:
        try:
            ts_clean = pd.Timestamp(date_str).strftime("%Y-%m-%d")
        except Exception:
            ts_clean = str(date_str or "").strip()
    direction = "IN" if str(tx_type or "").strip().lower() in {"income", "in", "credit", "+"} else "OUT"
    amt_int = int(round(abs(float(amount))))
    memo_norm = _norm_dedup_text(transfer_memo)
    cp_norm = _norm_dedup_text(counterparty)

    composite = f"{int(user_id)}|{ts_clean}|{direction}|{amt_int}|{memo_norm}|{cp_norm}"
    return "fp:" + hashlib.sha256(composite.encode("utf-8")).hexdigest()


def insert_transaction(
    user_id: int,
    date_str: str,
    description: str,
    amount: float,
    tx_type: str,
    category: str,
    is_auto_categorized: bool = True,
    category_confidence: float = 0.95,
    source_type: str = "quick_text",
    transfer_memo: str = "",
    ai_note: str = "",
    external_ref: str = "",
    tx_timestamp: str = "",
    counterparty: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Insert one newly captured transaction (Quick Text / Bill OCR / Bank Sync / Webhook) into SQLite."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO transactions
            (user_id, date, description, amount, type, category, is_auto_categorized,
             category_confidence, source_type, transfer_memo, ai_note, external_ref,
             tx_timestamp, counterparty, source_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                pd.Timestamp(date_str).strftime("%Y-%m-%d"),
                str(description).strip(),
                abs(float(amount)),
                "income" if tx_type == "income" else "expense",
                str(category),
                1 if is_auto_categorized else 0,
                float(category_confidence),
                str(source_type),
                str(transfer_memo),
                str(ai_note),
                str(external_ref).strip(),
                str(tx_timestamp).strip(),
                str(counterparty).strip(),
                source_type,
                now_iso,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def find_active_transaction_by_refs(
    user_id: int,
    candidate_refs: list[str],
    db_path: Path = DEFAULT_DB_PATH,
) -> int | None:
    """Check strictly against ACTIVE rows in `transactions` whether any candidate ref already exists.

    If a user deletes a synced transaction from `transactions`, this immediately returns None so
    the next Bank Sync preview scan re-discovers it cleanly.
    """
    clean_refs = list(dict.fromkeys(str(r or "").strip() for r in candidate_refs if str(r or "").strip()))
    if not clean_refs:
        return None
    init_db(db_path)
    placeholders = ",".join("?" for _ in clean_refs)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"SELECT id FROM transactions WHERE user_id = ? AND external_ref IN ({placeholders}) LIMIT 1",
            [int(user_id), *clean_refs],
        ).fetchone()
    return int(row[0]) if row else None


def insert_transaction_dedup(
    user_id: int,
    date_str: str,
    description: str,
    amount: float,
    tx_type: str,
    category: str,
    is_auto_categorized: bool = True,
    category_confidence: float = 0.95,
    source_type: str = "sepay_webhook",
    transfer_memo: str = "",
    ai_note: str = "",
    external_ref: str = "",
    tx_timestamp: str = "",
    counterparty: str = "",
    reference_code: str = "",
    provider: str = "",
    legacy_refs: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[int, bool]:
    """Insert a synced transaction with strict 2-tier deduplication & DB-level atomic uniqueness.

    Returns `(tx_id, is_duplicate)`.
    """
    init_db(db_path)
    ref_clean = str(external_ref or "").strip()
    if not ref_clean:
        ref_clean = build_transaction_unique_key(
            user_id=user_id,
            date_str=date_str,
            amount=amount,
            tx_type=tx_type,
            transfer_memo=transfer_memo,
            tx_timestamp=tx_timestamp,
            counterparty=counterparty,
            reference_code=reference_code,
            provider=provider or source_type,
        )

    candidate_refs = [ref_clean] + [str(r).strip() for r in (legacy_refs or []) if str(r or "").strip()]
    unique_candidates = list(dict.fromkeys(candidate_refs))

    with sqlite3.connect(db_path) as conn:
        placeholders = ",".join("?" for _ in unique_candidates)
        existing = conn.execute(
            f"SELECT id, external_ref FROM transactions WHERE user_id = ? AND external_ref IN ({placeholders}) LIMIT 1",
            [int(user_id), *unique_candidates],
        ).fetchone()
        if existing:
            ex_id, ex_ref = int(existing[0]), str(existing[1] or "")
            # Upgrade matched legacy key cleanly to the new canonical key so future rescans match directly
            if ex_ref != ref_clean:
                try:
                    conn.execute(
                        "UPDATE transactions SET external_ref = ?, tx_timestamp = CASE WHEN tx_timestamp='' THEN ? ELSE tx_timestamp END, counterparty = CASE WHEN counterparty='' THEN ? ELSE counterparty END WHERE id = ?",
                        (ref_clean, str(tx_timestamp).strip(), str(counterparty).strip(), ex_id),
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
            return ex_id, True

    try:
        tx_id = insert_transaction(
            user_id=user_id,
            date_str=date_str,
            description=description,
            amount=amount,
            tx_type=tx_type,
            category=category,
            is_auto_categorized=is_auto_categorized,
            category_confidence=category_confidence,
            source_type=source_type,
            transfer_memo=transfer_memo,
            ai_note=ai_note,
            external_ref=ref_clean,
            tx_timestamp=tx_timestamp,
            counterparty=counterparty,
            db_path=db_path,
        )
        return tx_id, False
    except sqlite3.IntegrityError:
        with sqlite3.connect(db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM transactions WHERE user_id = ? AND external_ref = ? LIMIT 1",
                (int(user_id), ref_clean),
            ).fetchone()
            if existing:
                return int(existing[0]), True
        raise


def log_webhook_event(
    user_id: int,
    provider: str,
    status: str,
    summary: str,
    amount: float = 0.0,
    tx_type: str = "expense",
    tx_id: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Record an incoming legal webhook / forwarding event for the live sync feed."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO webhook_events (user_id, provider, status, tx_id, summary, amount, tx_type, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(provider),
                str(status),
                int(tx_id) if tx_id is not None else None,
                str(summary)[:180],
                abs(float(amount)),
                "income" if tx_type == "income" else "expense",
                now_iso,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_recent_webhook_events(
    user_id: int,
    limit: int = 5,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Fetch recent auto-sync webhook/forwarding events for a user."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, provider, status, tx_id, summary, amount, tx_type, received_at
            FROM webhook_events
            WHERE user_id = ?
              AND (tx_id IS NULL OR tx_id IN (SELECT id FROM transactions WHERE user_id = ?))
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(user_id), int(user_id), int(limit)),
        ).fetchall()
    return [
        {
            "id": int(r[0]),
            "provider": r[1],
            "status": r[2],
            "tx_id": r[3],
            "summary": r[4],
            "amount": float(r[5]),
            "tx_type": r[6],
            "received_at": r[7],
        }
        for r in rows
    ]


def get_user_sync_signature(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> tuple[int, int]:
    """Ultra-fast signature `(tx_count, max_tx_id)` for real-time Streamlit auto-refresh."""
    if not db_path.exists():
        return 0, 0
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(MAX(id), 0) FROM transactions WHERE user_id = ?",
                (int(user_id),),
            ).fetchone()
        return int(row[0] or 0), int(row[1] or 0)
    except Exception:
        return 0, 0


def get_transactions_since_id(
    user_id: int,
    since_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Fetch transactions inserted after `since_id` so the UI can toast live incoming updates."""
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, date, description, amount, type, category, source_type, transfer_memo
            FROM transactions
            WHERE user_id = ? AND id > ?
            ORDER BY id ASC
            """,
            (int(user_id), int(since_id)),
        ).fetchall()
    return [
        {
            "id": int(r[0]),
            "date": r[1],
            "description": r[2],
            "amount": float(r[3]),
            "type": r[4],
            "category": r[5],
            "source_type": r[6],
            "transfer_memo": r[7],
        }
        for r in rows
    ]


def delete_transaction(tx_id: int, user_id: int, db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Hard-delete a single transaction belonging to user_id and clean up its sync feed link."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (int(tx_id), int(user_id)))
        conn.execute("DELETE FROM webhook_events WHERE user_id = ? AND tx_id = ?", (int(user_id), int(tx_id)))
        conn.commit()
        return cur.rowcount > 0


def load_transactions_from_db(
    user_id: int = 1,
    db_path: Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Load all transactions for a given user_id from SQLite."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT id, date, description, amount, type, category,
                   is_auto_categorized, category_confidence,
                   source_type, transfer_memo, ai_note
            FROM transactions
            WHERE user_id = ?
            ORDER BY date ASC, id ASC
            """,
            conn,
            params=(int(user_id),),
        )
    if df.empty:
        return pd.DataFrame(
            columns=[
                "id", "date", "description", "amount", "type", "category",
                "is_auto_categorized", "category_confidence",
                "source_type", "transfer_memo", "ai_note", "signed_amount", "year_month",
            ]
        )
    df["date"] = pd.to_datetime(df["date"])
    df["is_auto_categorized"] = df["is_auto_categorized"].astype(bool)
    df["signed_amount"] = np.where(df["type"] == "income", df["amount"], -df["amount"])
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    return df


def seed_user_demo_transactions(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Seed realistic Vietnamese 4-month transactions for a user account."""
    from src.categorization import categorize_transactions

    raw_df, err = parse_csv_source(SEED_DATA_PATH)
    if err or raw_df is None:
        return 0
    cleaned = clean_transactions(raw_df)
    categorized = categorize_transactions(cleaned)
    # Tag realistic source types (online bank transfers vs offline quick capture)
    online_kws = ("shopee", "tiktok", "momo", "spotify", "netflix", "icloud", "viettel", "fpt", "thuê phòng", "lương", "trợ cấp", "freelance", "grab", "xanh sm")
    sources = []
    memos = []
    for desc, tx_type in zip(categorized["description"], categorized["type"]):
        low = str(desc).lower()
        if any(k in low for k in online_kws):
            sources.append("bank_sync")
            if tx_type == "income":
                memos.append(f"CK DEN · {desc}")
            else:
                memos.append(f"TT ONLINE · {desc}")
        else:
            sources.append("quick_text")
            memos.append("")
    categorized["source_type"] = sources
    categorized["transfer_memo"] = memos
    return save_transactions_to_db(categorized, source_name="demo_seed", user_id=user_id, db_path=db_path)


def get_db_summary(user_id: int = 1, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return quick SQLite metadata for the active user."""
    if not db_path.exists():
        return {"exists": False, "rows": 0, "path": db_path.name}
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute(
                "SELECT COUNT(*), MAX(created_at) FROM transactions WHERE user_id = ?",
                (int(user_id),),
            )
            count, updated = cur.fetchone()
        return {"exists": True, "rows": int(count or 0), "updated_at": updated or "", "path": db_path.name}
    except Exception:
        return {"exists": False, "rows": 0, "path": db_path.name}


# ---------------------------------------------------------------------------
# App Settings, Fixed Monthly Expenses & Email Bank Sync Persistence
# ---------------------------------------------------------------------------
def get_app_setting(key: str, default: str = "", db_path: Path = DEFAULT_DB_PATH) -> str:
    """Read a persisted key-value setting (e.g. API key) from SQLite."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (str(key),)).fetchone()
    return str(row[0]) if row else default


def set_app_setting(key: str, value: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Persist a key-value setting in SQLite."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (str(key), str(value), now_iso),
        )
        conn.commit()


def load_fixed_expenses(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Load all user-defined fixed monthly expenses from SQLite."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, name, amount, category, due_day, note, created_at
            FROM fixed_expenses
            WHERE user_id = ?
            ORDER BY amount DESC, id ASC
            """,
            (int(user_id),),
        ).fetchall()
    return [
        {
            "id": int(r[0]),
            "name": str(r[1]),
            "amount": float(r[2]),
            "category": str(r[3]),
            "due_day": int(r[4]),
            "note": str(r[5] or ""),
            "created_at": str(r[6]),
        }
        for r in rows
    ]


def insert_fixed_expense(
    user_id: int,
    name: str,
    amount: float,
    category: str = "Bills",
    due_day: int = 1,
    note: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Insert a new user-defined fixed monthly expense."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    clean_day = min(max(int(due_day), 1), 31)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO fixed_expenses (user_id, name, amount, category, due_day, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(name).strip(),
                abs(float(amount)),
                str(category).strip() or "Bills",
                clean_day,
                str(note).strip(),
                now_iso,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def delete_fixed_expense(fixed_id: int, user_id: int, db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Delete a user-defined fixed monthly expense."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM fixed_expenses WHERE id = ? AND user_id = ?",
            (int(fixed_id), int(user_id)),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_transactions_bulk(tx_ids: list[int], user_id: int, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Hard-delete one or more transactions belonging to user_id and clean up their sync feed links."""
    init_db(db_path)
    ids = [int(i) for i in tx_ids]
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            f"DELETE FROM transactions WHERE user_id = ? AND id IN ({placeholders})",
            [int(user_id), *ids],
        )
        conn.execute(
            f"DELETE FROM webhook_events WHERE user_id = ? AND tx_id IN ({placeholders})",
            [int(user_id), *ids],
        )
        conn.commit()
        return int(cur.rowcount)


def get_email_sync_config(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Return Email Bank Auto-Sync config for user_id, or None if not configured."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT user_id, email_address, app_password_enc, imap_host, imap_port,
                   enabled, last_uid, last_checked_at, last_status, last_error, synced_count
            FROM email_sync_configs
            WHERE user_id = ?
            """,
            (int(user_id),),
        ).fetchone()
    if not row:
        return None
    return {
        "user_id": int(row[0]),
        "email_address": str(row[1]),
        "app_password_enc": str(row[2]),
        "imap_host": str(row[3] or "imap.gmail.com"),
        "imap_port": int(row[4] or 993),
        "enabled": bool(int(row[5] or 0)),
        "last_uid": int(row[6] or 0),
        "last_checked_at": str(row[7] or ""),
        "last_status": str(row[8] or ""),
        "last_error": str(row[9] or ""),
        "synced_count": int(row[10] or 0),
    }


def save_email_sync_config(
    user_id: int,
    email_address: str,
    app_password_enc: str,
    imap_host: str = "imap.gmail.com",
    imap_port: int = 993,
    enabled: bool = True,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Create or update a user's Email Bank Auto-Sync configuration."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO email_sync_configs
            (user_id, email_address, app_password_enc, imap_host, imap_port, enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email_address = excluded.email_address,
                app_password_enc = CASE WHEN excluded.app_password_enc != '' THEN excluded.app_password_enc ELSE email_sync_configs.app_password_enc END,
                imap_host = excluded.imap_host,
                imap_port = excluded.imap_port,
                enabled = excluded.enabled,
                updated_at = excluded.updated_at
            """,
            (
                int(user_id),
                str(email_address).strip().lower(),
                str(app_password_enc),
                str(imap_host).strip() or "imap.gmail.com",
                int(imap_port),
                1 if enabled else 0,
                now_iso,
            ),
        )
        conn.commit()


def update_email_sync_status(
    user_id: int,
    last_uid: int | None = None,
    last_status: str = "",
    last_error: str = "",
    added_count: int = 0,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Update last scan timestamp, UID watermark, status & error for a user's email sync."""
    init_db(db_path)
    now_iso = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        if last_uid is not None:
            conn.execute(
                """
                UPDATE email_sync_configs
                SET last_uid = ?, last_checked_at = ?, last_status = ?, last_error = ?,
                    synced_count = synced_count + ?, updated_at = ?
                WHERE user_id = ?
                """,
                (int(last_uid), now_iso, str(last_status), str(last_error), int(added_count), now_iso, int(user_id)),
            )
        else:
            conn.execute(
                """
                UPDATE email_sync_configs
                SET last_checked_at = ?, last_status = ?, last_error = ?,
                    synced_count = synced_count + ?, updated_at = ?
                WHERE user_id = ?
                """,
                (now_iso, str(last_status), str(last_error), int(added_count), now_iso, int(user_id)),
            )
        conn.commit()


def list_enabled_email_sync_configs(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Return all active Email Bank Sync configs for background polling."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT user_id, email_address, app_password_enc, imap_host, imap_port,
                   enabled, last_uid, last_checked_at, last_status, last_error, synced_count
            FROM email_sync_configs
            WHERE enabled = 1 AND email_address != '' AND app_password_enc != ''
            """
        ).fetchall()
    return [
        {
            "user_id": int(r[0]),
            "email_address": str(r[1]),
            "app_password_enc": str(r[2]),
            "imap_host": str(r[3] or "imap.gmail.com"),
            "imap_port": int(r[4] or 993),
            "enabled": bool(int(r[5] or 0)),
            "last_uid": int(r[6] or 0),
            "last_checked_at": str(r[7] or ""),
            "last_status": str(r[8] or ""),
            "last_error": str(r[9] or ""),
            "synced_count": int(r[10] or 0),
        }
        for r in rows
    ]
