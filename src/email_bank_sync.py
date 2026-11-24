"""Real-Time Bank Balance Email Auto-Sync Engine (IMAP SSL → AI Extraction → SQLite Table).

Pipeline (100% Legal — reads only emails the user explicitly connects via their own Email App Password):
1. User enables bank balance alert emails in their banking app (MBBank, VCB, TCB, ACB, TPBank, MoMo...).
2. User enters their Email & App Password and toggles Auto-Sync ON.
3. Background watcher polls INBOX (readonly) immediately for new bank alert emails via IMAP SSL.
4. AI (`generate_universal_reply` + Scikit-learn/regex fallback) extracts bank name, date, amount,
   income/expense direction, category, and transfer memo.
5. Deduplicated transaction is inserted directly into SQLite (`transactions` table) and the
   dashboard table/charts auto-refresh live!
"""

from __future__ import annotations

import email
import html as html_lib
import imaplib
import json
import re
import threading
import time
from datetime import date, datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from src.auth import get_user_by_id
from src.capture import (
    extract_account_or_counterparty,
    extract_exact_timestamp,
    extract_transaction_reference,
    parse_bank_notification,
)
from src.categorization import predict_single_transaction
from src.data_processing import (
    CANONICAL_EXPENSE_CATEGORIES,
    DEFAULT_DB_PATH,
    PROJECT_ROOT,
    build_transaction_unique_key,
    find_active_transaction_by_refs,
    get_email_sync_config,
    insert_transaction_dedup,
    list_enabled_email_sync_configs,
    log_webhook_event,
    save_email_sync_config,
    update_email_sync_status,
)
from src.llm_client import generate_universal_reply, resolve_saved_api_key

KEY_FILE_PATH = PROJECT_ROOT / "data" / ".email_sync.key"

BANK_EMAIL_HINTS = (
    "mbbank", "mb bank", "vietcombank", "vcb", "techcombank", "tcb", "acb", "tpbank", "tpb",
    "vpbank", "bidv", "smartbanking", "vietinbank", "agribank", "sacombank", "vib", "ocb", "msb",
    "shb", "hdbank", "eximbank", "seabank", "timo", "cake", "momo", "zalopay", "vnpay", "shinhan", "hsbc",
    "biến động số dư", "bien dong so du", "thông báo giao dịch", "thong bao giao dich",
    "biên lai chuyển tiền", "bien lai chuyen tien", "biên lai", "notice of successful transaction",
    "chuyển khoản", "chuyen khoan", "chuyển tiền", "chuyen tien", "ghi nợ", "ghi có",
    "transaction alert", "balance alert", "số tiền giao dịch", "transaction amount",
)

SAMPLE_BANK_EMAILS: list[dict[str, str]] = [
    {
        "label": "Email MBBank · Thanh toán ăn uống",
        "sender": "MBBank Alert <mbebanking@mbbank.com.vn>",
        "subject": "Thong bao bien dong so du tai khoan MBBank",
        "body": (
            "Kinh chao Quy khach,\n"
            "MBBank thong bao bien dong so du TK 0988xxx686:\n"
            "So tien giao dich: -165,000 VND\n"
            "Thoi gian: {hm} ngay {dmy}\n"
            "So du kha dung: 9,420,000 VND\n"
            "Noi dung giao dich: Thanh toan com trua va tra sua Phuc Long cung nhom"
        ),
    },
    {
        "label": "Email Vietcombank · Mua sắm Shopee",
        "sender": "Vietcombank Digibank <VCBDigibank@info.vietcombank.com.vn>",
        "subject": "Vietcombank - Thong bao bien dong so du",
        "body": (
            "Vietcombank thong bao giao dich ghi no tai khoan 1029xxx441:\n"
            "So tien: -420,000 VND vao luc {hm} {dmy}.\n"
            "Noi dung: Thanh toan don hang Shopee ban phim co van phong."
        ),
    },
    {
        "label": "Email Techcombank · Nhận thu nhập Freelance",
        "sender": "Techcombank <no-reply@techcombank.com.vn>",
        "subject": "Thong bao ghi co tai khoan Techcombank",
        "body": (
            "Techcombank thong bao TK 1903xxx882 vua nhan +2,500,000 VND luc {hm} {dmy}.\n"
            "Noi dung chuyen khoan: CTY DESIGN STUDIO thanh toan thu lao thiet ke UI thang nay."
        ),
    },
    {
        "label": "Email MoMo · Thanh toán tiền điện nước",
        "sender": "Vi MoMo <no-reply@momo.vn>",
        "subject": "Bien lai thanh toan hoa don dich vu MoMo",
        "body": (
            "Ban vua thanh toan thanh cong -580,000 VND qua Vi MoMo luc {hm} ngay {dmy}.\n"
            "Noi dung: Thanh toan hoa don tien dien EVN va Internet FPT hang thang."
        ),
    },
]

_WATCHER_LOCK = threading.Lock()
_WATCHER_THREAD: threading.Thread | None = None


def _get_fernet() -> Fernet:
    KEY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_FILE_PATH.exists():
        key = KEY_FILE_PATH.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        KEY_FILE_PATH.write_bytes(key)
    return Fernet(key)


def encrypt_app_password(raw_password: str) -> str:
    clean = str(raw_password or "").replace(" ", "").strip()
    if not clean:
        return ""
    return _get_fernet().encrypt(clean.encode("utf-8")).decode("utf-8")


def decrypt_app_password(enc_password: str) -> str:
    if not enc_password:
        return ""
    try:
        return _get_fernet().decrypt(enc_password.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _decode_header_str(raw: str | None) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    out = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            for enc in (charset or "utf-8", "utf-8", "cp1258", "latin1"):
                try:
                    out.append(chunk.decode(enc, errors="replace"))
                    break
                except Exception:
                    continue
        else:
            out.append(str(chunk))
    return " ".join(out).strip()


def _html_to_text(raw_html: str) -> str:
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
    cleaned = re.sub(r"<br\s*/?>|</p>|</tr>|</div>|</li>|</td>|</th>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html_lib.unescape(cleaned).replace("\xa0", " ")
    cleaned = re.sub(r"[ \t\r]+", " ", cleaned)
    cleaned = re.sub(r"(?: *\n *)+", "\n", cleaned)
    return cleaned.strip()


def _extract_email_body(msg: email.message.Message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except Exception:
                text = payload.decode("utf-8", errors="replace")
            if ctype == "text/plain":
                plain_parts.append(text)
            elif ctype == "text/html":
                html_parts.append(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except Exception:
                text = payload.decode("utf-8", errors="replace")
            if (msg.get_content_type() or "").lower() == "text/html":
                html_parts.append(text)
            else:
                plain_parts.append(text)

    if plain_parts:
        return "\n".join(plain_parts).strip()
    if html_parts:
        return _html_to_text("\n".join(html_parts))
    return ""


def _looks_like_bank_alert(sender: str, subject: str, body: str) -> bool:
    # Check full cleaned email body (up to 6000 chars) so bank HTML headers never push the amount out of window
    blob = f"{sender}\n{subject}\n{body[:6000]}".lower()
    has_bank_hint = any(h in blob for h in BANK_EMAIL_HINTS)
    has_money = bool(re.search(r"\d{1,3}(?:[.,]\d{3})+|\d+\s*(?:vnd|vnđ|đ|tr|k)\b", blob, flags=re.I))
    return has_bank_hint and has_money


def _parse_email_date_header(date_header: str) -> str:
    raw = str(date_header or "").strip()
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is not None:
                dt = dt.astimezone()
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return ""


def _clean_llm_ref(val: Any) -> str:
    s = str(val or "").strip()
    if not s or s.lower() in {"none", "null", "n/a", "khong co", "không có", "-", "empty"}:
        return ""
    if len(s) < 4 or not any(ch.isdigit() for ch in s):
        return ""
    return s


def _normalize_timestamp(val: Any, fallback: str = "") -> str:
    s = str(val or "").strip()
    if s:
        m = re.match(r"^(20\d{2}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?", s)
        if m:
            return f"{m.group(1)} {m.group(2)}:{m.group(3) or '00'}"
        parsed = extract_exact_timestamp(s, fallback_date="")
        if parsed:
            return parsed
    return fallback


def extract_bank_email_with_ai(
    sender: str,
    subject: str,
    body: str,
    monthly_budget: float = 8_000_000,
    api_key: str = "",
    email_date_header: str = "",
) -> dict[str, Any] | None:
    """Use AI LLM (when user API key is set or regex needs help) + Scikit-learn ML to extract bank emails."""
    today_str = date.today().strftime("%Y-%m-%d")
    full_text = f"{sender}\n{subject}\n{body}"
    email_ts_fallback = _parse_email_date_header(email_date_header)
    regex_ref = extract_transaction_reference(full_text)
    regex_ts = extract_exact_timestamp(full_text, fallback_date="")
    regex_cp = extract_account_or_counterparty(full_text)
    combined = f"From: {sender}\nSubject: {subject}\nDate: {email_date_header}\nBody:\n{body[:3500]}"
    has_private_key = bool(resolve_saved_api_key(api_key))

    # Fast local regex + ML parser first when no private API key is set (saves public LLM rate limit for chat!)
    if not has_private_key:
        quick_parsed = parse_bank_notification(f"{sender} {subject}\n{body}", monthly_budget=monthly_budget, api_key="")
        if quick_parsed is not None:
            q_ts = str(quick_parsed.get("tx_timestamp") or "").strip()
            if len(q_ts) <= 10:
                q_ts = regex_ts or email_ts_fallback or quick_parsed["date"]
            return {
                "bank_name": quick_parsed["bank_name"],
                "date": quick_parsed["date"],
                "tx_timestamp": q_ts,
                "reference_code": regex_ref or str(quick_parsed.get("reference_code") or "").strip(),
                "counterparty": regex_cp or str(quick_parsed.get("counterparty") or "").strip(),
                "description": quick_parsed["description"],
                "amount": quick_parsed["amount"],
                "type": quick_parsed["type"],
                "category": quick_parsed["category"],
                "confidence": quick_parsed["confidence"],
                "transfer_memo": quick_parsed["transfer_memo"],
                "ai_note": quick_parsed["ai_note"],
            }

    prompt = (
        "Bóc tách email thông báo biến động số dư ngân hàng sau và trả về DUY NHẤT 1 đối tượng JSON hợp lệ (không giải thích thêm):\n"
        '{"is_bank_transaction": true, "bank_name": "MBBank", "date": "YYYY-MM-DD", "tx_timestamp": "YYYY-MM-DD HH:MM:SS", '
        '"reference_code": "mã giao dịch hoặc số tham chiếu nếu có, để trống nếu không có", '
        '"counterparty": "tên hoặc số tài khoản người gửi/nhận nếu có", "amount": 150000, '
        '"type": "expense", "category": "Food|Shopping|Transport|Bills|Entertainment|Other|Income", '
        '"description": "mô tả ngắn gọn dễ hiểu", "transfer_memo": "nội dung chuyển khoản gốc", '
        '"ai_note": "nhận xét ngắn gọn 1 câu bằng tiếng Việt"}\n'
        f"Quy tắc: Nếu KHÔNG phải thông báo giao dịch/biến động số dư thật thì đặt is_bank_transaction=false. "
        f"Nếu thiếu ngày dùng {today_str}. type chỉ nhận 'income' (tiền vào/ghi có/+) hoặc 'expense' (tiền ra/ghi nợ/-). "
        "amount luôn là số dương VND. Giữ nguyên chính xác reference_code và tx_timestamp đến từng giây nếu có trong email.\n\n"
        f"{combined}"
    )

    llm_txt, llm_src = generate_universal_reply(
        user_message=prompt,
        system_instruction="Bạn là bộ bóc tách dữ liệu giao dịch tài chính ngân hàng Việt Nam. Chỉ xuất JSON chuẩn.",
        api_key=api_key,
        max_tokens=420,
        temperature=0.1,
    )
    if llm_txt:
        m_json = re.search(r"\{.*\}", llm_txt, flags=re.S)
        if m_json:
            try:
                data = json.loads(m_json.group(0))
                if data.get("is_bank_transaction") is False:
                    return None
                amt = abs(float(data.get("amount") or 0))
                if amt > 0:
                    tx_type = "income" if str(data.get("type", "")).lower() == "income" else "expense"
                    bank_name = str(data.get("bank_name") or "Email Bank").strip()
                    memo = str(data.get("transfer_memo") or subject).strip()
                    desc = str(data.get("description") or f"{bank_name} · {memo[:55]}").strip()
                    cat = str(data.get("category") or "").strip()
                    if tx_type == "income":
                        cat = "Income"
                    elif cat not in CANONICAL_EXPENSE_CATEGORIES:
                        cat, _, _ = predict_single_transaction(f"{bank_name} {desc} {memo}", tx_type)
                    tx_date = str(data.get("date") or today_str).strip()
                    if not re.match(r"^20\d{2}-\d{2}-\d{2}$", tx_date):
                        tx_date = today_str
                    ref_code = regex_ref or _clean_llm_ref(data.get("reference_code"))
                    tx_ts = regex_ts or _normalize_timestamp(data.get("tx_timestamp"), fallback="") or email_ts_fallback or tx_date
                    llm_cp = str(data.get("counterparty") or "").strip()
                    if llm_cp.lower() in {"none", "null", "n/a", "khong co", "không có", "-"}:
                        llm_cp = ""
                    counterparty = regex_cp or llm_cp
                    return {
                        "bank_name": bank_name,
                        "date": tx_date,
                        "tx_timestamp": tx_ts,
                        "reference_code": ref_code,
                        "counterparty": counterparty,
                        "description": desc,
                        "amount": amt,
                        "type": tx_type,
                        "category": cat,
                        "confidence": 0.96,
                        "transfer_memo": memo,
                        "ai_note": str(data.get("ai_note") or f"AI ({llm_src}) tự động bóc tách từ Email ngân hàng."),
                    }
            except Exception:
                pass

    # Rock-solid regex + Scikit-learn ML fallback
    parsed = parse_bank_notification(f"{sender} {subject}\n{body}", monthly_budget=monthly_budget, api_key="")
    if parsed is None:
        return None
    p_ts = str(parsed.get("tx_timestamp") or "").strip()
    if len(p_ts) <= 10:
        p_ts = regex_ts or email_ts_fallback or parsed["date"]
    return {
        "bank_name": parsed["bank_name"],
        "date": parsed["date"],
        "tx_timestamp": p_ts,
        "reference_code": regex_ref or str(parsed.get("reference_code") or "").strip(),
        "counterparty": regex_cp or str(parsed.get("counterparty") or "").strip(),
        "description": parsed["description"],
        "amount": parsed["amount"],
        "type": parsed["type"],
        "category": parsed["category"],
        "confidence": parsed["confidence"],
        "transfer_memo": parsed["transfer_memo"],
        "ai_note": parsed["ai_note"],
    }


def save_and_test_email_config(
    user_id: int,
    email_address: str,
    raw_app_password: str,
    imap_host: str = "imap.gmail.com",
    imap_port: int = 993,
    enabled: bool = True,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[bool, str]:
    """Verify IMAP credentials live and save encrypted Email Bank Sync settings in SQLite."""
    addr = str(email_address or "").strip().lower()
    if not addr or "@" not in addr:
        return False, "Vui lòng nhập địa chỉ Email hợp lệ."

    existing = get_email_sync_config(user_id, db_path=db_path)
    clean_pw = str(raw_app_password or "").replace(" ", "").strip()
    if not clean_pw and existing and existing.get("app_password_enc"):
        clean_pw = decrypt_app_password(existing["app_password_enc"])
    if not clean_pw:
        return False, "Vui lòng nhập Mật khẩu ứng dụng (App Password 16 ký tự của Gmail/Email)."

    # Live IMAP SSL login test
    try:
        with imaplib.IMAP4_SSL(imap_host.strip() or "imap.gmail.com", int(imap_port), timeout=10) as mail:
            mail.login(addr, clean_pw)
            mail.select("INBOX", readonly=True)
    except imaplib.IMAP4.error as exc:
        return False, f"Đăng nhập IMAP thất bại (kiểm tra lại Email & App Password 16 ký tự): {exc}"
    except Exception as exc:
        return False, f"Không thể kết nối máy chủ IMAP ({imap_host}): {exc}"

    enc_pw = encrypt_app_password(clean_pw) if raw_app_password.strip() else (existing["app_password_enc"] if existing else encrypt_app_password(clean_pw))
    save_email_sync_config(
        user_id=user_id,
        email_address=addr,
        app_password_enc=enc_pw,
        imap_host=imap_host,
        imap_port=imap_port,
        enabled=enabled,
        db_path=db_path,
    )
    update_email_sync_status(
        user_id=user_id,
        last_status="Đã kết nối IMAP thành công",
        last_error="",
        db_path=db_path,
    )
    return True, "Kết nối Email ngân hàng thành công! Hệ thống sẽ tự động quét email biến động số dư mới ngay lập tức."


def scan_user_bank_emails_now(
    user_id: int,
    api_key: str = "",
    max_emails: int = 25,
    rescan_recent_days: int = 0,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Scan user's IMAP INBOX right now for new bank balance emails, extract with AI, and insert into SQLite.

    When `rescan_recent_days > 0` (used by the manual 'Quét Email ngay lập tức' button), scans recent
    days' emails and relies on `Message-ID` deduplication so previously missed bank alerts are recovered
    without ever creating duplicates.
    """
    cfg = get_email_sync_config(user_id, db_path=db_path)
    if not cfg or not cfg["email_address"] or not cfg["app_password_enc"]:
        return {"ok": False, "inserted": 0, "scanned": 0, "error": "Chưa cấu hình Email & App Password."}

    user = get_user_by_id(user_id, db_path=db_path)
    if user is None:
        return {"ok": False, "inserted": 0, "scanned": 0, "error": "Không tìm thấy người dùng."}

    app_pw = decrypt_app_password(cfg["app_password_enc"])
    if not app_pw:
        return {"ok": False, "inserted": 0, "scanned": 0, "error": "Không giải mã được App Password, vui lòng nhập lại."}

    active_key = resolve_saved_api_key(api_key)
    inserted = 0
    scanned = 0
    highest_uid = int(cfg["last_uid"] or 0)
    added_items: list[dict[str, Any]] = []

    try:
        with imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg["imap_port"]), timeout=12) as mail:
            mail.login(cfg["email_address"], app_pw)
            mail.select("INBOX", readonly=True)

            if rescan_recent_days > 0 or highest_uid <= 0:
                lookback = rescan_recent_days if rescan_recent_days > 0 else 7
                since_str = (datetime.now() - timedelta(days=lookback)).strftime("%d-%b-%Y")
                status, data = mail.uid("search", None, f"(SINCE {since_str})")
            else:
                status, data = mail.uid("search", None, f"UID {highest_uid + 1}:*")

            if status != "OK" or not data or not data[0]:
                update_email_sync_status(user_id, last_status="Đã quét — chưa có email mới", last_error="", db_path=db_path)
                return {"ok": True, "inserted": 0, "scanned": 0, "items": []}

            uids = sorted(int(u) for u in data[0].split() if u.isdigit())
            if rescan_recent_days <= 0 and highest_uid > 0:
                uids = [u for u in uids if u > highest_uid]
            if not uids:
                update_email_sync_status(user_id, last_status="Đã quét — chưa có email mới", last_error="", db_path=db_path)
                return {"ok": True, "inserted": 0, "scanned": 0, "items": []}

            failed_uid: int | None = None
            for uid in uids[-max_emails:]:
                f_status, msg_data = mail.uid("fetch", str(uid), "(RFC822)")
                if f_status != "OK" or not msg_data:
                    if failed_uid is None:
                        failed_uid = uid
                    continue
                raw_bytes = None
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) >= 2:
                        raw_bytes = part[1]
                        break
                if not raw_bytes:
                    if failed_uid is None:
                        failed_uid = uid
                    continue

                msg = email.message_from_bytes(raw_bytes)
                sender = _decode_header_str(msg.get("From"))
                subject = _decode_header_str(msg.get("Subject"))
                email_date_hdr = str(msg.get("Date") or "").strip()
                body = _extract_email_body(msg)
                scanned += 1

                if not _looks_like_bank_alert(sender, subject, body):
                    if failed_uid is None:
                        highest_uid = max(highest_uid, uid)
                    continue

                extracted = extract_bank_email_with_ai(
                    sender=sender,
                    subject=subject,
                    body=body,
                    monthly_budget=float(user["monthly_budget"]),
                    api_key=active_key,
                    email_date_header=email_date_hdr,
                )
                if not extracted:
                    if failed_uid is None:
                        highest_uid = max(highest_uid, uid)
                    continue

                msg_id = str(msg.get("Message-ID") or f"uid_{uid}").strip()
                canonical_key = build_transaction_unique_key(
                    user_id=user_id,
                    date_str=extracted["date"],
                    amount=extracted["amount"],
                    tx_type=extracted["type"],
                    transfer_memo=extracted["transfer_memo"],
                    tx_timestamp=extracted.get("tx_timestamp", ""),
                    counterparty=extracted.get("counterparty", ""),
                    reference_code=extracted.get("reference_code", ""),
                    provider=extracted["bank_name"],
                )
                legacy_refs = [f"email:{msg_id[:90]}"]
                if len(msg_id) > 90:
                    legacy_refs.append(f"email:{msg_id}")

                tx_id, is_dup = insert_transaction_dedup(
                    user_id=user_id,
                    date_str=extracted["date"],
                    description=extracted["description"],
                    amount=extracted["amount"],
                    tx_type=extracted["type"],
                    category=extracted["category"],
                    is_auto_categorized=True,
                    category_confidence=extracted["confidence"],
                    source_type="email_bank_sync",
                    transfer_memo=extracted["transfer_memo"],
                    ai_note=extracted["ai_note"],
                    external_ref=canonical_key,
                    tx_timestamp=extracted.get("tx_timestamp", ""),
                    counterparty=extracted.get("counterparty", ""),
                    reference_code=extracted.get("reference_code", ""),
                    provider=extracted["bank_name"],
                    legacy_refs=legacy_refs,
                    db_path=db_path,
                )
                if failed_uid is None:
                    highest_uid = max(highest_uid, uid)
                if not is_dup:
                    inserted += 1
                    log_webhook_event(
                        user_id=user_id,
                        provider=f"Email · {extracted['bank_name']}",
                        status="synced",
                        summary=f"{extracted['description']} → {extracted['category']}",
                        amount=extracted["amount"],
                        tx_type=extracted["type"],
                        tx_id=tx_id,
                        db_path=db_path,
                    )
                    added_items.append(extracted)

        status_msg = (
            f"Đã tự động đồng bộ {inserted} giao dịch mới từ Email"
            if inserted > 0
            else f"Đã quét {scanned} email mới — không có biến động mới"
        )
        update_email_sync_status(
            user_id=user_id,
            last_uid=highest_uid,
            last_status=status_msg,
            last_error="",
            added_count=inserted,
            db_path=db_path,
        )
        return {"ok": True, "inserted": inserted, "scanned": scanned, "items": added_items}
    except Exception as exc:
        err_str = str(exc)
        update_email_sync_status(user_id=user_id, last_status="Lỗi quét Email", last_error=err_str[:220], db_path=db_path)
        return {"ok": False, "inserted": inserted, "scanned": scanned, "error": err_str}


def _detect_bank_name_quick(text: str) -> str:
    low = str(text or "").lower()
    for name, kws in (
        ("MBBank", ("mbbank", "mb bank", "mb:")),
        ("Vietcombank", ("vietcombank", "vcb:", "vcb ")),
        ("Techcombank", ("techcombank", "tcb:", "tcb ")),
        ("ACB", ("acb:", "ngan hang acb", "acb.com.vn")),
        ("TPBank", ("tpbank", "tpb:")),
        ("VPBank", ("vpbank", "vpb:")),
        ("BIDV", ("bidv", "smartbanking")),
        ("VietinBank", ("vietinbank", "ctg:")),
        ("Agribank", ("agribank",)),
        ("MoMo", ("momo",)),
        ("ZaloPay", ("zalopay",)),
    ):
        if any(k in low for k in kws):
            return name
    return ""


def preview_user_bank_emails(
    user_id: int,
    api_key: str = "",
    lookback_days: int = 7,
    max_emails: int = 50,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Step 1 (Scan & Preview): Scan IMAP INBOX without writing to DB.

    NEVER filters by `last_uid` and checks ONLY against currently ACTIVE rows in `transactions`.
    If the user deleted a previously synced transaction from the web table, it will be cleanly
    re-discovered here as an importable candidate.
    """
    cfg = get_email_sync_config(user_id, db_path=db_path)
    if not cfg or not cfg["email_address"] or not cfg["app_password_enc"]:
        return {"ok": False, "scanned": 0, "skipped_active": 0, "candidates": [], "error": "Chưa cấu hình Email & App Password."}

    user = get_user_by_id(user_id, db_path=db_path)
    if user is None:
        return {"ok": False, "scanned": 0, "skipped_active": 0, "candidates": [], "error": "Không tìm thấy người dùng."}

    app_pw = decrypt_app_password(cfg["app_password_enc"])
    if not app_pw:
        return {"ok": False, "scanned": 0, "skipped_active": 0, "candidates": [], "error": "Không giải mã được App Password, vui lòng nhập lại."}

    active_key = resolve_saved_api_key(api_key)
    days = max(1, int(lookback_days or 7))
    scanned = 0
    skipped_active = 0
    candidates: list[dict[str, Any]] = []
    seen_preview_keys: set[str] = set()

    try:
        with imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg["imap_port"]), timeout=12) as mail:
            mail.login(cfg["email_address"], app_pw)
            mail.select("INBOX", readonly=True)

            since_str = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            status, data = mail.uid("search", None, f"(SINCE {since_str})")
            if status != "OK" or not data or not data[0]:
                update_email_sync_status(
                    user_id=user_id,
                    last_status=f"Đã quét xem trước ({days} ngày) — không có email",
                    last_error="",
                    db_path=db_path,
                )
                return {
                    "ok": True,
                    "scanned": 0,
                    "skipped_active": 0,
                    "candidates": [],
                    "lookback_days": days,
                }

            uids = sorted(int(u) for u in data[0].split() if u.isdigit())
            for uid in uids[-max_emails:]:
                f_status, msg_data = mail.uid("fetch", str(uid), "(RFC822)")
                if f_status != "OK" or not msg_data:
                    continue
                raw_bytes = None
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) >= 2:
                        raw_bytes = part[1]
                        break
                if not raw_bytes:
                    continue

                msg = email.message_from_bytes(raw_bytes)
                sender = _decode_header_str(msg.get("From"))
                subject = _decode_header_str(msg.get("Subject"))
                email_date_hdr = str(msg.get("Date") or "").strip()
                body = _extract_email_body(msg)
                scanned += 1

                if not _looks_like_bank_alert(sender, subject, body):
                    continue

                msg_id = str(msg.get("Message-ID") or f"uid_{uid}").strip()
                legacy_refs = [f"email:{msg_id[:90]}"]
                if len(msg_id) > 90:
                    legacy_refs.append(f"email:{msg_id}")

                # Fast active-data pre-check: skip expensive LLM call ONLY if row is CURRENTLY active in DB
                pre_refs = list(legacy_refs)
                quick_ref = extract_transaction_reference(f"{sender}\n{subject}\n{body}")
                quick_bank = _detect_bank_name_quick(f"{sender}\n{subject}\n{body}")
                if quick_ref and quick_bank:
                    pre_refs.append(
                        build_transaction_unique_key(
                            user_id=user_id,
                            date_str=date.today().strftime("%Y-%m-%d"),
                            amount=1.0,
                            tx_type="expense",
                            reference_code=quick_ref,
                            provider=quick_bank,
                        )
                    )
                if find_active_transaction_by_refs(user_id=user_id, candidate_refs=pre_refs, db_path=db_path) is not None:
                    skipped_active += 1
                    continue

                extracted = extract_bank_email_with_ai(
                    sender=sender,
                    subject=subject,
                    body=body,
                    monthly_budget=float(user["monthly_budget"]),
                    api_key=active_key,
                    email_date_header=email_date_hdr,
                )
                if not extracted:
                    continue

                canonical_key = build_transaction_unique_key(
                    user_id=user_id,
                    date_str=extracted["date"],
                    amount=extracted["amount"],
                    tx_type=extracted["type"],
                    transfer_memo=extracted["transfer_memo"],
                    tx_timestamp=extracted.get("tx_timestamp", ""),
                    counterparty=extracted.get("counterparty", ""),
                    reference_code=extracted.get("reference_code", ""),
                    provider=extracted["bank_name"],
                )

                # Strict check ONLY against currently active rows in `transactions`
                if find_active_transaction_by_refs(
                    user_id=user_id,
                    candidate_refs=[canonical_key, *legacy_refs],
                    db_path=db_path,
                ) is not None:
                    skipped_active += 1
                    continue

                if canonical_key in seen_preview_keys:
                    continue
                seen_preview_keys.add(canonical_key)

                candidates.append(
                    {
                        "unique_key": canonical_key,
                        "legacy_refs": legacy_refs,
                        "uid": uid,
                        "bank_name": extracted["bank_name"],
                        "date": extracted["date"],
                        "tx_timestamp": extracted.get("tx_timestamp") or extracted["date"],
                        "reference_code": extracted.get("reference_code", ""),
                        "counterparty": extracted.get("counterparty", ""),
                        "description": extracted["description"],
                        "amount": float(extracted["amount"]),
                        "type": extracted["type"],
                        "category": extracted["category"],
                        "confidence": float(extracted.get("confidence", 0.95)),
                        "transfer_memo": extracted["transfer_memo"],
                        "ai_note": extracted["ai_note"],
                        "source_type": "email_bank_sync",
                    }
                )

        # Sort newest first so recent/just-deleted transactions appear at the top
        candidates.sort(key=lambda item: (str(item.get("tx_timestamp") or item.get("date") or ""), int(item.get("uid") or 0)), reverse=True)

        status_msg = (
            f"Đã quét xem trước ({days} ngày): tìm thấy {len(candidates)} giao dịch chưa có trên web"
            if candidates
            else f"Đã quét {scanned} email ({days} ngày) — tất cả đều đã có trên web"
        )
        update_email_sync_status(
            user_id=user_id,
            last_status=status_msg,
            last_error="",
            db_path=db_path,
        )
        return {
            "ok": True,
            "scanned": scanned,
            "skipped_active": skipped_active,
            "candidates": candidates,
            "lookback_days": days,
        }
    except Exception as exc:
        err_str = str(exc)
        update_email_sync_status(user_id=user_id, last_status="Lỗi quét xem trước Email", last_error=err_str[:220], db_path=db_path)
        return {
            "ok": False,
            "scanned": scanned,
            "skipped_active": skipped_active,
            "candidates": [],
            "lookback_days": days,
            "error": err_str,
        }


def import_selected_bank_transactions(
    user_id: int,
    selected_items: list[dict[str, Any]],
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Step 2 (Confirm & Import): Persist ONLY the user-checked preview transactions into SQLite."""
    inserted = 0
    duplicates = 0
    tx_ids: list[int] = []
    max_uid = 0

    for item in selected_items:
        uid_val = int(item.get("uid") or 0)
        if uid_val > max_uid:
            max_uid = uid_val

        canonical_key = str(item.get("unique_key") or "").strip()
        if not canonical_key:
            canonical_key = build_transaction_unique_key(
                user_id=user_id,
                date_str=str(item.get("date") or date.today().strftime("%Y-%m-%d")),
                amount=float(item.get("amount") or 0),
                tx_type=str(item.get("type") or "expense"),
                transfer_memo=str(item.get("transfer_memo") or ""),
                tx_timestamp=str(item.get("tx_timestamp") or ""),
                counterparty=str(item.get("counterparty") or ""),
                reference_code=str(item.get("reference_code") or ""),
                provider=str(item.get("bank_name") or "Email Bank"),
            )

        tx_id, is_dup = insert_transaction_dedup(
            user_id=user_id,
            date_str=str(item.get("date") or date.today().strftime("%Y-%m-%d")),
            description=str(item.get("description") or "Giao dịch ngân hàng"),
            amount=float(item.get("amount") or 0),
            tx_type=str(item.get("type") or "expense"),
            category=str(item.get("category") or "Other"),
            is_auto_categorized=True,
            category_confidence=float(item.get("confidence") or 0.95),
            source_type=str(item.get("source_type") or "email_bank_sync"),
            transfer_memo=str(item.get("transfer_memo") or ""),
            ai_note=str(item.get("ai_note") or ""),
            external_ref=canonical_key,
            tx_timestamp=str(item.get("tx_timestamp") or ""),
            counterparty=str(item.get("counterparty") or ""),
            reference_code=str(item.get("reference_code") or ""),
            provider=str(item.get("bank_name") or "Email Bank"),
            legacy_refs=list(item.get("legacy_refs") or []),
            db_path=db_path,
        )
        if is_dup:
            duplicates += 1
        else:
            inserted += 1
            tx_ids.append(tx_id)
            log_webhook_event(
                user_id=user_id,
                provider=f"Email · {item.get('bank_name') or 'Bank'}",
                status="synced",
                summary=f"{item.get('description') or ''} → {item.get('category') or 'Other'}",
                amount=float(item.get("amount") or 0),
                tx_type=str(item.get("type") or "expense"),
                tx_id=tx_id,
                db_path=db_path,
            )

    cfg = get_email_sync_config(user_id, db_path=db_path)
    if cfg is not None:
        cur_uid = int(cfg.get("last_uid") or 0)
        new_uid = max(cur_uid, max_uid) if max_uid > 0 else None
        update_email_sync_status(
            user_id=user_id,
            last_uid=new_uid,
            last_status=f"Đã thêm {inserted} giao dịch đã chọn vào dữ liệu",
            last_error="",
            added_count=inserted,
            db_path=db_path,
        )

    return {"ok": True, "inserted": inserted, "duplicates": duplicates, "tx_ids": tx_ids}


def simulate_bank_email_preview(
    user: dict[str, Any],
    sample_index: int = 0,
    api_key: str = "",
) -> dict[str, Any]:
    """Run a sample bank alert email through AI extraction and return a preview candidate (no DB write yet)."""
    sample = SAMPLE_BANK_EMAILS[sample_index % len(SAMPLE_BANK_EMAILS)]
    now = datetime.now()
    body = sample["body"].format(hm=now.strftime("%H:%M"), dmy=now.strftime("%d/%m/%Y"))

    extracted = extract_bank_email_with_ai(
        sender=sample["sender"],
        subject=sample["subject"],
        body=body,
        monthly_budget=float(user["monthly_budget"]),
        api_key=api_key,
        email_date_header=now.strftime("%a, %d %b %Y %H:%M:%S +0700"),
    )
    if not extracted:
        return {"ok": False, "error": "AI không trích xuất được giao dịch từ email mẫu."}

    unique_key = build_transaction_unique_key(
        user_id=int(user["id"]),
        date_str=extracted["date"],
        amount=float(extracted["amount"]),
        tx_type=extracted["type"],
        transfer_memo=extracted["transfer_memo"],
        tx_timestamp=extracted.get("tx_timestamp") or now.strftime("%Y-%m-%d %H:%M:%S"),
        counterparty=extracted.get("counterparty", ""),
        reference_code=extracted.get("reference_code") or f"DEMO{int(time.time() * 1000)}",
        provider=extracted["bank_name"],
    )
    candidate = {
        "unique_key": unique_key,
        "legacy_refs": [],
        "uid": 0,
        "bank_name": extracted["bank_name"],
        "date": extracted["date"],
        "tx_timestamp": extracted.get("tx_timestamp") or now.strftime("%Y-%m-%d %H:%M:%S"),
        "reference_code": extracted.get("reference_code", ""),
        "counterparty": extracted.get("counterparty", ""),
        "description": extracted["description"],
        "amount": float(extracted["amount"]),
        "type": extracted["type"],
        "category": extracted["category"],
        "confidence": float(extracted.get("confidence", 0.95)),
        "transfer_memo": extracted["transfer_memo"],
        "ai_note": extracted["ai_note"],
        "source_type": "email_bank_sync",
    }
    return {
        "ok": True,
        "scanned": 1,
        "skipped_active": 0,
        "candidates": [candidate],
        "lookback_days": 1,
    }


def simulate_bank_email_scan(
    user: dict[str, Any],
    sample_index: int = 0,
    api_key: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Run a realistic bank alert email through the EXACT AI extraction → SQLite table pipeline."""
    sample = SAMPLE_BANK_EMAILS[sample_index % len(SAMPLE_BANK_EMAILS)]
    now = datetime.now()
    body = sample["body"].format(hm=now.strftime("%H:%M"), dmy=now.strftime("%d/%m/%Y"))

    extracted = extract_bank_email_with_ai(
        sender=sample["sender"],
        subject=sample["subject"],
        body=body,
        monthly_budget=float(user["monthly_budget"]),
        api_key=api_key,
    )
    if not extracted:
        return {"ok": False, "error": "AI không trích xuất được giao dịch từ email mẫu."}

    ext_ref = f"email_demo:{int(time.time() * 1000)}"
    tx_id, is_dup = insert_transaction_dedup(
        user_id=user["id"],
        date_str=extracted["date"],
        description=extracted["description"],
        amount=extracted["amount"],
        tx_type=extracted["type"],
        category=extracted["category"],
        is_auto_categorized=True,
        category_confidence=extracted["confidence"],
        source_type="email_bank_sync",
        transfer_memo=extracted["transfer_memo"],
        ai_note=extracted["ai_note"],
        external_ref=ext_ref,
        tx_timestamp=extracted.get("tx_timestamp", ""),
        counterparty=extracted.get("counterparty", ""),
        reference_code=extracted.get("reference_code", ""),
        provider=extracted["bank_name"],
        db_path=db_path,
    )
    log_webhook_event(
        user_id=user["id"],
        provider=f"Email AI · {extracted['bank_name']}",
        status="duplicate" if is_dup else "synced",
        summary=f"{extracted['description']} → {extracted['category']}",
        amount=extracted["amount"],
        tx_type=extracted["type"],
        tx_id=tx_id,
        db_path=db_path,
    )
    return {"ok": True, "transaction_id": tx_id, "extracted": extracted}


def ensure_email_watcher_running(poll_seconds: int = 12) -> bool:
    """Start a single background daemon thread that auto-scans enabled users' bank emails immediately."""
    global _WATCHER_THREAD
    with _WATCHER_LOCK:
        if _WATCHER_THREAD is not None and _WATCHER_THREAD.is_alive():
            return True

        def _loop() -> None:
            while True:
                try:
                    configs = list_enabled_email_sync_configs()
                    for cfg in configs:
                        scan_user_bank_emails_now(user_id=cfg["user_id"], max_emails=10)
                except Exception:
                    pass
                time.sleep(poll_seconds)

        _WATCHER_THREAD = threading.Thread(target=_loop, name="moneylens-email-sync", daemon=True)
        _WATCHER_THREAD.start()
        return True
