"""100% Legal Real-Time Bank Auto-Sync Webhook Server (SePay / Casso / PayOS / Notification Forwarding).

Runs an embedded Starlette + Uvicorn HTTP listener on port 8502 (configurable via WEBHOOK_PORT)
alongside MoneyLens AI so real bank balance alerts arrive directly into SQLite and automatically
refresh the user's live dashboard without ever touching bank passwords or scraping banking apps.

Supported 100% legal read-only channels:
1. POST /api/webhook/sepay/{token}    — SePay.vn official read-only Webhook
2. POST /api/webhook/casso/{token}    — Casso.vn official read-only Webhook
3. POST /api/webhook/payos/{token}    — PayOS official read-only Webhook
4. POST /api/webhook/forward/{token}  — User-consented SMS / Email / iOS Shortcuts / Android MacroDroid Forwarding
5. GET  /api/webhook/health           — Health check endpoint

Can also be launched standalone behind Nginx / Cloudflare Tunnel / ngrok:
    python -m src.webhook_server
"""

from __future__ import annotations

import hashlib
import os
import random
import re
import socket
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from src.auth import get_user_by_webhook_token
from src.capture import (
    extract_account_or_counterparty,
    extract_exact_timestamp,
    extract_transaction_reference,
    parse_bank_notification,
)
from src.categorization import predict_single_transaction
from src.data_processing import (
    DEFAULT_DB_PATH,
    build_transaction_unique_key,
    insert_transaction_dedup,
    log_webhook_event,
)

DEFAULT_WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8502"))

_SERVER_LOCK = threading.Lock()
_SERVER_THREAD: threading.Thread | None = None
_ACTIVE_PORT: int = DEFAULT_WEBHOOK_PORT


def get_webhook_port() -> int:
    return _ACTIVE_PORT


def get_webhook_base_url() -> str:
    """Return configured public URL (e.g. Cloudflare Tunnel / ngrok / domain) or local receiver URL."""
    pub = os.getenv("WEBHOOK_PUBLIC_URL", "").strip().rstrip("/")
    if pub:
        return pub
    return f"http://127.0.0.1:{_ACTIVE_PORT}"


def _parse_iso_or_vn_date(raw: Any) -> str:
    """Parse '2026-11-22 14:23:00', '22/11/2026', ISO timestamp, or fallback to today."""
    s = str(raw or "").strip()
    if not s:
        return date.today().strftime("%Y-%m-%d")
    m_ymd = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m_ymd:
        try:
            return date(int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3))).strftime("%Y-%m-%d")
        except ValueError:
            pass
    m_dmy = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", s)
    if m_dmy:
        try:
            return date(int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1))).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date.today().strftime("%Y-%m-%d")


def _parse_iso_or_vn_timestamp(raw: Any, fallback_date: str = "") -> str:
    """Parse exact 'YYYY-MM-DD HH:MM:SS' from webhook timestamp fields, or fallback to date."""
    s = str(raw or "").strip()
    if s:
        parsed = extract_exact_timestamp(s, fallback_date="")
        if parsed:
            return parsed
    return fallback_date or _parse_iso_or_vn_date(raw)


def _extract_counterparty_from_payload(payload: dict[str, Any]) -> str:
    """Collect sender/recipient name or account fields from structured gateway payloads."""
    keys = (
        "counterAccountName",
        "counterAccountNumber",
        "corresponsiveName",
        "corresponsiveAccount",
        "subAccount",
        "accountNumber",
        "bank_sub_acc_id",
    )
    parts: list[str] = []
    for k in keys:
        v = str(payload.get(k) or "").strip()
        if v and v not in parts:
            parts.append(v)
    return " | ".join(parts)


def _analyze_structured_transfer(
    bank_name: str,
    amount: float,
    tx_type: str,
    memo: str,
    tx_date: str,
    monthly_budget: float,
) -> dict[str, Any]:
    """Run ML categorization + AI contextual memo analysis on a structured gateway payload."""
    synthetic_alert = (
        f"{bank_name}: {'+' if tx_type == 'income' else '-'}{int(round(abs(amount))):,} VND "
        f"ngay {tx_date}. ND: {memo}"
    )
    parsed = parse_bank_notification(synthetic_alert, monthly_budget=monthly_budget, api_key="")
    if parsed is not None:
        parsed["bank_name"] = bank_name or parsed["bank_name"]
        parsed["date"] = tx_date
        parsed["amount"] = abs(float(amount))
        parsed["type"] = "income" if tx_type == "income" else "expense"
        parsed["transfer_memo"] = memo
        parsed["description"] = f"{parsed['bank_name']} · {memo[:64]}" if memo else f"Giao dịch {parsed['bank_name']}"
        return parsed

    cat, conf, method = predict_single_transaction(f"{bank_name} {memo}", tx_type)
    return {
        "bank_name": bank_name,
        "date": tx_date,
        "description": f"{bank_name} · {memo[:64]}" if memo else f"Giao dịch {bank_name}",
        "amount": abs(float(amount)),
        "type": "income" if tx_type == "income" else "expense",
        "category": cat,
        "confidence": conf,
        "method": method,
        "transfer_memo": memo,
        "ai_note": f"Tự động đồng bộ từ {bank_name} ({method}, {int(round(conf * 100))}%).",
    }


def _check_optional_secret(user: dict[str, Any], request: Request) -> bool:
    """Validate optional shared secret header when the user has configured one."""
    secret = str(user.get("webhook_secret") or "").strip()
    if not secret:
        return True
    auth_hdr = str(request.headers.get("authorization", "")).strip()
    sec_hdr = str(request.headers.get("secure-token", "")).strip()
    x_sec = str(request.headers.get("x-webhook-secret", "")).strip()
    candidates = [sec_hdr, x_sec]
    if auth_hdr.lower().startswith("apikey "):
        candidates.append(auth_hdr[7:].strip())
    elif auth_hdr.lower().startswith("bearer "):
        candidates.append(auth_hdr[7:].strip())
    return secret in candidates


# ---------------------------------------------------------------------------
# Core Processor Functions (Also directly callable in unit tests!)
# ---------------------------------------------------------------------------
def process_sepay_payload(
    user: dict[str, Any],
    payload: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Ingest official SePay.vn read-only webhook JSON payload into SQLite."""
    gateway = str(payload.get("gateway") or payload.get("bankName") or "SePay Bank").strip()
    raw_amt = float(payload.get("transferAmount") or payload.get("amount") or 0)
    if raw_amt <= 0:
        return {"ok": False, "error": "transferAmount must be > 0"}

    tr_type = str(payload.get("transferType") or "out").strip().lower()
    tx_type = "income" if tr_type in {"in", "credit", "income", "+"} else "expense"
    memo = str(payload.get("content") or payload.get("description") or "").strip()
    tx_date = _parse_iso_or_vn_date(payload.get("transactionDate"))
    tx_ts = _parse_iso_or_vn_timestamp(payload.get("transactionDate"), fallback_date=tx_date)
    explicit_ref = str(payload.get("referenceCode") or "").strip()
    gateway_id = str(payload.get("id") or "").strip()
    memo_ref = extract_transaction_reference(memo)
    ref_code = explicit_ref or memo_ref or gateway_id
    ref_provider = gateway if (explicit_ref or memo_ref) else "sepay"
    counterparty = _extract_counterparty_from_payload(payload) or extract_account_or_counterparty(memo)
    legacy_raw = explicit_ref or gateway_id
    legacy_refs = [f"sepay:{legacy_raw}"] if legacy_raw else []

    analyzed = _analyze_structured_transfer(
        bank_name=gateway,
        amount=raw_amt,
        tx_type=tx_type,
        memo=memo,
        tx_date=tx_date,
        monthly_budget=float(user["monthly_budget"]),
    )
    canonical_key = build_transaction_unique_key(
        user_id=user["id"],
        date_str=analyzed["date"],
        amount=analyzed["amount"],
        tx_type=analyzed["type"],
        transfer_memo=memo,
        tx_timestamp=tx_ts,
        counterparty=counterparty,
        reference_code=ref_code,
        provider=ref_provider,
    )
    tx_id, is_dup = insert_transaction_dedup(
        user_id=user["id"],
        date_str=analyzed["date"],
        description=analyzed["description"],
        amount=analyzed["amount"],
        tx_type=analyzed["type"],
        category=analyzed["category"],
        is_auto_categorized=True,
        category_confidence=analyzed["confidence"],
        source_type="sepay_webhook",
        transfer_memo=memo,
        ai_note=analyzed["ai_note"],
        external_ref=canonical_key,
        tx_timestamp=tx_ts,
        counterparty=counterparty,
        reference_code=ref_code,
        provider=ref_provider,
        legacy_refs=legacy_refs,
        db_path=db_path,
    )
    log_webhook_event(
        user_id=user["id"],
        provider="SePay",
        status="duplicate" if is_dup else "synced",
        summary=f"{analyzed['description']} → {analyzed['category']}",
        amount=analyzed["amount"],
        tx_type=analyzed["type"],
        tx_id=tx_id,
        db_path=db_path,
    )
    return {
        "ok": True,
        "provider": "SePay",
        "inserted": 0 if is_dup else 1,
        "duplicates": 1 if is_dup else 0,
        "transaction_id": tx_id,
        "category": analyzed["category"],
        "description": analyzed["description"],
        "amount": analyzed["amount"],
        "type": analyzed["type"],
    }


def process_casso_payload(
    user: dict[str, Any],
    payload: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Ingest official Casso.vn read-only webhook JSON payload (batch `data` array supported)."""
    items = payload.get("data")
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items:
        return {"ok": False, "error": "Casso payload requires non-empty `data` list"}

    inserted = 0
    duplicates = 0
    processed: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        raw_amt = float(item.get("amount") or 0)
        if raw_amt == 0:
            continue
        tx_type = "income" if raw_amt > 0 else "expense"
        abs_amt = abs(raw_amt)
        bank_name = str(item.get("bankName") or item.get("bank_sub_acc_id") or "Casso Bank").strip()
        memo = str(item.get("description") or "").strip()
        raw_when = item.get("when") or item.get("transactionDateTime")
        tx_date = _parse_iso_or_vn_date(raw_when)
        tx_ts = _parse_iso_or_vn_timestamp(raw_when, fallback_date=tx_date)
        explicit_tid = str(item.get("tid") or "").strip()
        gateway_id = str(item.get("id") or "").strip()
        memo_ref = extract_transaction_reference(memo)
        ref_code = explicit_tid or memo_ref or gateway_id
        ref_provider = bank_name if (explicit_tid or memo_ref) else "casso"
        counterparty = _extract_counterparty_from_payload(item) or extract_account_or_counterparty(memo)
        legacy_raw = explicit_tid or gateway_id
        legacy_refs = [f"casso:{legacy_raw}"] if legacy_raw else []

        analyzed = _analyze_structured_transfer(
            bank_name=bank_name,
            amount=abs_amt,
            tx_type=tx_type,
            memo=memo,
            tx_date=tx_date,
            monthly_budget=float(user["monthly_budget"]),
        )
        canonical_key = build_transaction_unique_key(
            user_id=user["id"],
            date_str=analyzed["date"],
            amount=analyzed["amount"],
            tx_type=analyzed["type"],
            transfer_memo=memo,
            tx_timestamp=tx_ts,
            counterparty=counterparty,
            reference_code=ref_code,
            provider=ref_provider,
        )
        tx_id, is_dup = insert_transaction_dedup(
            user_id=user["id"],
            date_str=analyzed["date"],
            description=analyzed["description"],
            amount=analyzed["amount"],
            tx_type=analyzed["type"],
            category=analyzed["category"],
            is_auto_categorized=True,
            category_confidence=analyzed["confidence"],
            source_type="casso_webhook",
            transfer_memo=memo,
            ai_note=analyzed["ai_note"],
            external_ref=canonical_key,
            tx_timestamp=tx_ts,
            counterparty=counterparty,
            reference_code=ref_code,
            provider=ref_provider,
            legacy_refs=legacy_refs,
            db_path=db_path,
        )
        if is_dup:
            duplicates += 1
        else:
            inserted += 1
        log_webhook_event(
            user_id=user["id"],
            provider="Casso",
            status="duplicate" if is_dup else "synced",
            summary=f"{analyzed['description']} → {analyzed['category']}",
            amount=analyzed["amount"],
            tx_type=analyzed["type"],
            tx_id=tx_id,
            db_path=db_path,
        )
        processed.append({"transaction_id": tx_id, "category": analyzed["category"], "duplicate": is_dup})

    return {
        "ok": True,
        "provider": "Casso",
        "inserted": inserted,
        "duplicates": duplicates,
        "transactions": processed,
    }


def process_payos_payload(
    user: dict[str, Any],
    payload: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Ingest official PayOS read-only webhook JSON payload into SQLite."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    raw_amt = float(data.get("amount") or 0)
    if raw_amt == 0:
        return {"ok": False, "error": "PayOS payload requires non-zero `amount`"}

    direction = str(data.get("transferType") or ("in" if raw_amt > 0 and not data.get("isExpense") else "out")).lower()
    tx_type = "income" if direction in {"in", "income", "credit"} and not data.get("isExpense") else "expense"
    memo = str(data.get("description") or "").strip()
    bank_name = str(data.get("counterAccountBankName") or "PayOS VietQR").strip()
    tx_date = _parse_iso_or_vn_date(data.get("transactionDateTime"))
    tx_ts = _parse_iso_or_vn_timestamp(data.get("transactionDateTime"), fallback_date=tx_date)
    explicit_ref = str(data.get("reference") or "").strip()
    order_code = str(data.get("orderCode") or "").strip()
    memo_ref = extract_transaction_reference(memo)
    ref_code = explicit_ref or memo_ref or order_code
    ref_provider = bank_name if (explicit_ref or memo_ref) else "payos"
    counterparty = _extract_counterparty_from_payload(data) or extract_account_or_counterparty(memo)
    legacy_raw = explicit_ref or order_code
    legacy_refs = [f"payos:{legacy_raw}"] if legacy_raw else []

    analyzed = _analyze_structured_transfer(
        bank_name=bank_name,
        amount=abs(raw_amt),
        tx_type=tx_type,
        memo=memo,
        tx_date=tx_date,
        monthly_budget=float(user["monthly_budget"]),
    )
    canonical_key = build_transaction_unique_key(
        user_id=user["id"],
        date_str=analyzed["date"],
        amount=analyzed["amount"],
        tx_type=analyzed["type"],
        transfer_memo=memo,
        tx_timestamp=tx_ts,
        counterparty=counterparty,
        reference_code=ref_code,
        provider=ref_provider,
    )
    tx_id, is_dup = insert_transaction_dedup(
        user_id=user["id"],
        date_str=analyzed["date"],
        description=analyzed["description"],
        amount=analyzed["amount"],
        tx_type=analyzed["type"],
        category=analyzed["category"],
        is_auto_categorized=True,
        category_confidence=analyzed["confidence"],
        source_type="payos_webhook",
        transfer_memo=memo,
        ai_note=analyzed["ai_note"],
        external_ref=canonical_key,
        tx_timestamp=tx_ts,
        counterparty=counterparty,
        reference_code=ref_code,
        provider=ref_provider,
        legacy_refs=legacy_refs,
        db_path=db_path,
    )
    log_webhook_event(
        user_id=user["id"],
        provider="PayOS",
        status="duplicate" if is_dup else "synced",
        summary=f"{analyzed['description']} → {analyzed['category']}",
        amount=analyzed["amount"],
        tx_type=analyzed["type"],
        tx_id=tx_id,
        db_path=db_path,
    )
    return {
        "ok": True,
        "provider": "PayOS",
        "inserted": 0 if is_dup else 1,
        "duplicates": 1 if is_dup else 0,
        "transaction_id": tx_id,
        "category": analyzed["category"],
        "description": analyzed["description"],
        "amount": analyzed["amount"],
        "type": analyzed["type"],
    }


def process_forward_payload(
    user: dict[str, Any],
    raw_text: str,
    source_label: str = "SMS/Notif Forward",
    external_ref: str = "",
    received_at: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Ingest a user-forwarded SMS / Email / Push Notification alert (iOS Shortcuts, MacroDroid, Gmail)."""
    parsed = parse_bank_notification(raw_text, monthly_budget=float(user["monthly_budget"]), api_key="")
    if parsed is None:
        return {"ok": False, "error": "Could not detect valid transaction amount in forwarded alert text"}

    explicit_ref = str(external_ref or "").strip()
    ref_code = explicit_ref or str(parsed.get("reference_code") or "").strip() or extract_transaction_reference(raw_text)
    tx_ts = str(parsed.get("tx_timestamp") or "").strip()
    if len(tx_ts) <= 10 and str(received_at or "").strip():
        tx_ts = _parse_iso_or_vn_timestamp(received_at, fallback_date=parsed["date"])
    if not tx_ts:
        tx_ts = parsed["date"]
    counterparty = str(parsed.get("counterparty") or "").strip() or extract_account_or_counterparty(raw_text)

    canonical_key = build_transaction_unique_key(
        user_id=user["id"],
        date_str=parsed["date"],
        amount=parsed["amount"],
        tx_type=parsed["type"],
        transfer_memo=parsed["transfer_memo"],
        tx_timestamp=tx_ts,
        counterparty=counterparty,
        reference_code=ref_code,
        provider=parsed["bank_name"],
    )
    legacy_refs: list[str] = []
    if explicit_ref:
        legacy_refs.append(explicit_ref)
    if not str(received_at or "").strip():
        legacy_refs.append("fwd:" + hashlib.sha256(f"{user['id']}|{raw_text.strip()}".encode("utf-8")).hexdigest()[:20])

    tx_id, is_dup = insert_transaction_dedup(
        user_id=user["id"],
        date_str=parsed["date"],
        description=parsed["description"],
        amount=parsed["amount"],
        tx_type=parsed["type"],
        category=parsed["category"],
        is_auto_categorized=True,
        category_confidence=parsed["confidence"],
        source_type="auto_forward",
        transfer_memo=parsed["transfer_memo"],
        ai_note=parsed["ai_note"],
        external_ref=canonical_key,
        tx_timestamp=tx_ts,
        counterparty=counterparty,
        reference_code=ref_code,
        provider=parsed["bank_name"],
        legacy_refs=legacy_refs,
        db_path=db_path,
    )
    log_webhook_event(
        user_id=user["id"],
        provider=source_label,
        status="duplicate" if is_dup else "synced",
        summary=f"{parsed['description']} → {parsed['category']}",
        amount=parsed["amount"],
        tx_type=parsed["type"],
        tx_id=tx_id,
        db_path=db_path,
    )
    return {
        "ok": True,
        "provider": source_label,
        "inserted": 0 if is_dup else 1,
        "duplicates": 1 if is_dup else 0,
        "transaction_id": tx_id,
        "category": parsed["category"],
        "description": parsed["description"],
        "amount": parsed["amount"],
        "type": parsed["type"],
    }


# ---------------------------------------------------------------------------
# Starlette HTTP Routes
# ---------------------------------------------------------------------------
async def _route_health(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "MoneyLens AI Legal Bank Webhook Receiver",
            "port": _ACTIVE_PORT,
            "channels": ["sepay", "casso", "payos", "forward"],
        }
    )


async def _handle_webhook(request: Request) -> JSONResponse:
    provider = request.path_params["provider"].lower().strip()
    token = request.path_params["token"].strip()
    user = get_user_by_webhook_token(token)
    if user is None:
        return JSONResponse({"ok": False, "error": "Invalid webhook token"}, status_code=401)
    if not _check_optional_secret(user, request):
        return JSONResponse({"ok": False, "error": "Invalid webhook secret header"}, status_code=403)

    content_type = (request.headers.get("content-type") or "").lower()
    raw_body = (await request.body()).decode("utf-8", errors="replace").strip()

    if provider == "forward":
        text_msg = ""
        src_lbl = "Notification Forward"
        ext_ref = ""
        received_at = ""
        if "json" in content_type:
            try:
                data = await request.json()
                text_msg = str(
                    data.get("text")
                    or data.get("message")
                    or data.get("body")
                    or data.get("content")
                    or ""
                ).strip()
                src_lbl = str(data.get("source") or "Notification Forward").strip()
                ext_ref = str(data.get("ref_id") or data.get("id") or "").strip()
                received_at = str(data.get("timestamp") or data.get("received_at") or data.get("date") or "").strip()
            except Exception:
                text_msg = raw_body
        else:
            text_msg = raw_body
        res = process_forward_payload(
            user, text_msg, source_label=src_lbl, external_ref=ext_ref, received_at=received_at
        )
        return JSONResponse(res, status_code=200 if res.get("ok") else 400)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)

    if provider == "sepay":
        res = process_sepay_payload(user, payload)
    elif provider == "casso":
        res = process_casso_payload(user, payload)
    elif provider == "payos":
        res = process_payos_payload(user, payload)
    else:
        return JSONResponse({"ok": False, "error": f"Unknown provider: {provider}"}, status_code=404)

    return JSONResponse(res, status_code=200 if res.get("ok") else 400)


webhook_app = Starlette(
    routes=[
        Route("/api/webhook/health", _route_health, methods=["GET"]),
        Route("/api/webhook/{provider:str}/{token:str}", _handle_webhook, methods=["POST"]),
    ]
)
webhook_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def is_webhook_server_healthy(port: int | None = None) -> bool:
    p = port or _ACTIVE_PORT
    try:
        r = requests.get(f"http://127.0.0.1:{p}/api/webhook/health", timeout=0.6)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def ensure_webhook_server_running(port: int = DEFAULT_WEBHOOK_PORT) -> tuple[bool, int]:
    """Start the embedded Webhook HTTP receiver once per process (safe on Streamlit reruns)."""
    global _SERVER_THREAD, _ACTIVE_PORT
    with _SERVER_LOCK:
        _ACTIVE_PORT = port
        if is_webhook_server_healthy(port):
            return True, port
        if _SERVER_THREAD is not None and _SERVER_THREAD.is_alive():
            return True, port

        # If default port is occupied by another unrelated service, find a nearby free port
        chosen_port = port
        if _is_port_open("127.0.0.1", chosen_port) and not is_webhook_server_healthy(chosen_port):
            for cand in range(port + 1, port + 15):
                if not _is_port_open("127.0.0.1", cand):
                    chosen_port = cand
                    break
        _ACTIVE_PORT = chosen_port

        def _run_uvicorn() -> None:
            config = uvicorn.Config(
                app=webhook_app,
                host="0.0.0.0",
                port=chosen_port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)
            server.install_signal_handlers = lambda: None  # type: ignore[assignment]
            server.run()

        _SERVER_THREAD = threading.Thread(target=_run_uvicorn, name="moneylens-webhook", daemon=True)
        _SERVER_THREAD.start()

    # Wait briefly until health endpoint responds
    for _ in range(25):
        if is_webhook_server_healthy(_ACTIVE_PORT):
            return True, _ACTIVE_PORT
        time.sleep(0.1)
    return is_webhook_server_healthy(_ACTIVE_PORT), _ACTIVE_PORT


# ---------------------------------------------------------------------------
# Live End-to-End Test Trigger (Fires a REAL HTTP POST to the Running Receiver!)
# ---------------------------------------------------------------------------
_LIVE_TEST_SCENARIOS: dict[str, list[dict[str, Any]]] = {
    "sepay": [
        {
            "gateway": "MBBank",
            "transferType": "out",
            "transferAmount": 145_000,
            "content": "Thanh toan tra sua Phuc Long va banh ngot",
        },
        {
            "gateway": "Vietcombank",
            "transferType": "out",
            "transferAmount": 320_000,
            "content": "Thanh toan don hang Shopee tai nghe bluetooth",
        },
        {
            "gateway": "Techcombank",
            "transferType": "in",
            "transferAmount": 1_500_000,
            "content": "Nhan thu lao du an Freelance UI Design",
        },
    ],
    "casso": [
        {
            "bankName": "Vietcombank",
            "amount": -265_000,
            "description": "MBVCB thanh toan hoa don tien dien EVN thang 11",
        },
        {
            "bankName": "MBBank",
            "amount": -88_000,
            "description": "GrabBike di chuyen len truong va ve nha",
        },
        {
            "bankName": "ACB",
            "amount": 2_000_000,
            "description": "Chuyen khoan ho tro sinh hoat phi thang 11",
        },
    ],
    "payos": [
        {
            "counterAccountBankName": "PayOS · VietQR",
            "amount": 195_000,
            "isExpense": True,
            "description": "Thanh toan ve xem phim CGV cuoi tuan",
        },
        {
            "counterAccountBankName": "PayOS · VietQR",
            "amount": 75_000,
            "isExpense": True,
            "description": "Thanh toan com trua van phong Highlands",
        },
    ],
    "forward": [
        {
            "source": "iOS Shortcut · MBBank",
            "text": "MBBank: TK 0988xxx686 -115,000 VND luc {time} {dmy}. ND: Thanh toan xang dau Petrolimex",
        },
        {
            "source": "Android MacroDroid · MoMo",
            "text": "MoMo: Ban vua thanh toan -240,000d luc {time} {dmy}. Noi dung: Chia tien an lau nhom ban",
        },
        {
            "source": "Gmail Forwarding · VCB",
            "text": "VCB: TK 1029xxx441 +1,200,000 VND luc {time} {dmy}. ND: Hoan tien dat coc & thuong du an",
        },
    ],
}


def send_live_test_webhook(provider: str, webhook_token: str, secret: str = "") -> tuple[bool, dict[str, Any]]:
    """Fire a REAL HTTP POST request to the live embedded Webhook Receiver to verify auto-sync."""
    ok, port = ensure_webhook_server_running()
    if not ok:
        return False, {"error": "Webhook server is not running"}

    prov = provider.lower().strip()
    now = datetime.now()
    uniq = f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
    iso_dt = now.strftime("%Y-%m-%d %H:%M:%S")
    dmy = now.strftime("%d/%m/%Y")
    hm = now.strftime("%H:%M")

    headers = {"Content-Type": "application/json"}
    if secret.strip():
        headers["Authorization"] = f"Apikey {secret.strip()}"
        headers["secure-token"] = secret.strip()

    if prov == "sepay":
        sc = random.choice(_LIVE_TEST_SCENARIOS["sepay"])
        body = {
            "id": int(time.time()) % 10_000_000,
            "gateway": sc["gateway"],
            "transactionDate": iso_dt,
            "accountNumber": "0988xxx686",
            "transferType": sc["transferType"],
            "transferAmount": sc["transferAmount"],
            "content": sc["content"],
            "referenceCode": f"SEPAY_{uniq}",
        }
    elif prov == "casso":
        sc = random.choice(_LIVE_TEST_SCENARIOS["casso"])
        body = {
            "error": 0,
            "data": [
                {
                    "id": int(time.time()) % 10_000_000,
                    "tid": f"CASSO_{uniq}",
                    "description": sc["description"],
                    "amount": sc["amount"],
                    "when": iso_dt,
                    "bankName": sc["bankName"],
                }
            ],
        }
    elif prov == "payos":
        sc = random.choice(_LIVE_TEST_SCENARIOS["payos"])
        body = {
            "code": "00",
            "desc": "success",
            "data": {
                "orderCode": int(time.time()) % 10_000_000,
                "amount": sc["amount"],
                "isExpense": sc["isExpense"],
                "description": sc["description"],
                "transactionDateTime": iso_dt,
                "counterAccountBankName": sc["counterAccountBankName"],
                "reference": f"PAYOS_{uniq}",
            },
        }
    else:
        prov = "forward"
        sc = random.choice(_LIVE_TEST_SCENARIOS["forward"])
        body = {
            "source": sc["source"],
            "text": sc["text"].format(time=hm, dmy=dmy),
            "ref_id": f"FWD_{uniq}",
        }

    url = f"http://127.0.0.1:{port}/api/webhook/{prov}/{webhook_token}"
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=4.0)
        return resp.status_code == 200, resp.json()
    except Exception as exc:
        return False, {"error": str(exc)}


if __name__ == "__main__":
    print(f"[MoneyLens AI] Starting Legal Bank Webhook Receiver on http://0.0.0.0:{DEFAULT_WEBHOOK_PORT}")
    uvicorn.run(webhook_app, host="0.0.0.0", port=DEFAULT_WEBHOOK_PORT)
