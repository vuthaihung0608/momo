"""Intelligent Transaction Capture Engine (Quick Text, Bill Image OCR & Online Bank Transfer Analysis).

Replaces manual CSV uploads with 3 real-world capture channels:
1. Quick Text Offline Entry (e.g. "Xăng 100k", "Highlands 45k", "Nhận lương 8.5tr")
2. Receipt / Bill Image OCR via Gemini 2.5 Flash Vision (with editable offline fallback)
3. Online Bank Transfer / Balance Alert Parser + AI Memo Analyzer (MB, VCB, TCB, ACB, TPBank, MoMo...)
"""

from __future__ import annotations

import io
import json
import os
import re
from datetime import date, datetime
from typing import Any

from src.categorization import predict_single_transaction
from src.llm_client import generate_gemini_vision, generate_universal_reply, resolve_saved_api_key

INCOME_KEYWORDS = (
    "lương", "luong", "thu nhập", "thu nhap", "nhận ", "nhan ", "trợ cấp", "tro cap",
    "freelance", "thưởng", "thuong", "hoàn tiền", "hoan tien", "cộng ", "cong ", "salary",
    "bonus", "income", "tiền về", "tien ve", "chuyển đến", "chuyen den", "ghi có", "ghi co",
)

SAMPLE_BANK_NOTIFICATIONS: list[dict[str, str]] = [
    {
        "label": "MBBank · Chuyển tiền phòng trọ",
        "text": "MBBank: TK 0988xxx686 -3,200,000 VND luc 08:15 22/11/2026. SD: 12,451,000 VND. ND: Chuyen khoan tien thue phong tro thang 12",
    },
    {
        "label": "Vietcombank · Nhận lương thực tập",
        "text": "VCB: TK 1029xxx441 +8,500,000 VND luc 09:00 22/11/2026. ND: CTY CONG NGHE ABC thanh toan luong thuc tap thang 11/2026",
    },
    {
        "label": "Techcombank · Thanh toán Shopee",
        "text": "Techcombank: TK 1903xxx882 -485,000 VND ngay 22/11/2026. Noi dung: Thanh toan don hang Shopee ban phim co va chuot khong day",
    },
    {
        "label": "MoMo · Chia tiền lẩu nhóm",
        "text": "MoMo: Ban vua chuyen thanh cong -360,000d cho TRAN THI LAN luc 20:45 21/11/2026. Loi nhan: Chia tien an lau Haidilao nhom du an",
    },
]


def _parse_amount_from_text(text: str) -> tuple[float | None, str]:
    """Extract VND numeric value and return (amount, remaining_description)."""
    s = text.strip()
    # Match patterns like 15tr, 1.5 triệu, 100k, 45.5k, 1,200,000d, 450000 vnd
    patterns = [
        (r"([+-]?\s*\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)\b", 1_000_000.0),
        (r"([+-]?\s*\d+(?:[.,]\d+)?)\s*(?:nghìn|nghin|ngàn|ngan|k)\b", 1_000.0),
        (r"([+-]?\s*\d{1,3}(?:[.,]\d{3})+)\s*(?:vnd|vnđ|đ|d)?\b", 1.0),
        (r"([+-]?\s*\d{4,10})\s*(?:vnd|vnđ|đ|d)?\b", 1.0),
    ]
    for pat, mult in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            raw_num = m.group(1).replace(" ", "")
            if mult == 1.0:
                clean_num = raw_num.replace(",", "").replace(".", "")
            else:
                clean_num = raw_num.replace(",", ".")
            try:
                val = abs(float(clean_num)) * mult
                if val > 0:
                    remainder = (s[: m.start()] + " " + s[m.end() :]).strip()
                    remainder = re.sub(r"\s+", " ", remainder).strip(" -,:;.")
                    return round(val), remainder
            except ValueError:
                continue
    return None, s


def _detect_date_from_text(text: str) -> str:
    """Detect DD/MM/YYYY or YYYY-MM-DD in text, else default to today."""
    m_dmy = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", text)
    if m_dmy:
        d, mo, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        try:
            return date(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass
    m_ymd = re.search(r"\b(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m_ymd:
        y, mo, d = int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3))
        try:
            return date(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date.today().strftime("%Y-%m-%d")


def extract_transaction_reference(text: str) -> str:
    """Extract official bank Transaction ID / Reference Code (Priority 1 unique key)."""
    s = str(text or "")
    if not s.strip():
        return ""
    labeled_patterns = [
        r"\b(?:Số tham chiếu|So tham chieu|Reference number|Ref(?:erence)?\s*(?:No\.?|Code|ID)|Mã giao dịch|Ma giao dich|Mã GD|Ma GD|MGD|Transaction\s*ID|Trans\s*ID|Số chứng từ|So chung tu|Trace\s*(?:No\.?|ID)?)\b\s*[:\-]?\s*(?:(?:Reference number|Transaction ID|Ref No\.?)\s*[:\-]?\s*)?([A-Za-z0-9][A-Za-z0-9._/\-]{4,48})",
    ]
    for pat in labeled_patterns:
        for m in re.finditer(pat, s, flags=re.IGNORECASE):
            cand = m.group(1).strip(" .,:;-")
            if len(cand) >= 5 and any(ch.isdigit() for ch in cand):
                return cand
    # Unlabeled well-known Vietnam banking trace IDs (FT..., MBVCB...., BIDV...)
    m_known = re.search(r"\b(FT\d{8,18}|MBVCB\.\d{6,18}|\d{4}BIDV[A-Z0-9]{6,18})\b", s)
    if m_known:
        return m_known.group(1).strip()
    return ""


def extract_exact_timestamp(text: str, fallback_date: str = "") -> str:
    """Extract precise YYYY-MM-DD HH:MM:SS timestamp from bank alert/email text."""
    s = str(text or "")
    # 1. DD/MM/YYYY HH:MM[:SS] or DD-MM-YYYY HH:MM[:SS]
    m1 = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})[\s,T]+(\d{1,2}):(\d{2})(?::(\d{2}))?\b", s)
    if m1:
        d, mo, y, hh, mm, ss = int(m1.group(1)), int(m1.group(2)), int(m1.group(3)), int(m1.group(4)), int(m1.group(5)), int(m1.group(6) or 0)
        try:
            return datetime(y, mo, d, hh, mm, ss).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    # 2. YYYY-MM-DD HH:MM[:SS] or ISO
    m2 = re.search(r"\b(20\d{2})[/-](\d{1,2})[/-](\d{1,2})[\s,T]+(\d{1,2}):(\d{2})(?::(\d{2}))?\b", s)
    if m2:
        y, mo, d, hh, mm, ss = int(m2.group(1)), int(m2.group(2)), int(m2.group(3)), int(m2.group(4)), int(m2.group(5)), int(m2.group(6) or 0)
        try:
            return datetime(y, mo, d, hh, mm, ss).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    # 3. HH:MM[:SS] ... DD/MM/YYYY (e.g. "luc 08:15 22/11/2026" or "20:45 ngay 21/11/2026")
    m3 = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(?:ngay|ngày)?\s*(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", s, flags=re.IGNORECASE)
    if m3:
        hh, mm, ss, d, mo, y = int(m3.group(1)), int(m3.group(2)), int(m3.group(3) or 0), int(m3.group(4)), int(m3.group(5)), int(m3.group(6))
        try:
            return datetime(y, mo, d, hh, mm, ss).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return fallback_date


def extract_account_or_counterparty(text: str) -> str:
    """Extract recipient/sender name or account number for composite deduplication."""
    s = str(text or "")
    parts: list[str] = []
    # Beneficiary / Recipient / Sender name (supports multi-line bilingual bank HTML tables like BIDV)
    m_name = re.search(
        r"(?:Tên người thụ hưởng|Ten nguoi thu huong|Beneficiary name|Người nhận|Nguoi nhan|Người gửi|Nguoi gui|Sender name)\s*[:\-]?\s*(?:(?:Beneficiary name|Recipient name|Sender name)\s*[:\-]?\s*)?([^\n]{2,64})",
        s,
        flags=re.IGNORECASE,
    )
    if m_name:
        nm = m_name.group(1).strip(" :;-")
        if nm and nm.lower() not in {"beneficiary name", "sender name"}:
            parts.append(nm)
    else:
        m_cho = re.search(r"\b(?:cho|tới|toi|từ|tu)\s+([A-ZÀ-Ỹ][A-ZÀ-Ỹ\s]{3,42})(?:\s+(?:luc|lúc|ngay|ngày|vao|vào)\b|[.,\n])", s)
        if m_cho:
            parts.append(m_cho.group(1).strip())

    # Beneficiary / Source account number
    m_ben_acc = re.search(
        r"(?:Số tài khoản(?:/Số thẻ)? thụ hưởng|Tài khoản thụ hưởng|Beneficiary account(?:/ Card number)?|TK nhận)\s*[:\-]?\s*(?:(?:Beneficiary account(?:/ Card number)?)\s*[:\-]?\s*)?([A-Za-z0-9*xX]{5,24})",
        s,
        flags=re.IGNORECASE,
    )
    if m_ben_acc:
        parts.append(m_ben_acc.group(1).strip())
    else:
        m_tk = re.search(r"\b(?:TK|Tài khoản nguồn|Debit account)\s*[:\-]?\s*(?:Debit account\s*[:\-]?\s*)?([A-Za-z0-9*xX]{5,20})", s, flags=re.IGNORECASE)
        if m_tk:
            parts.append(m_tk.group(1).strip())

    return " | ".join(dict.fromkeys(p for p in parts if p))


def parse_quick_text(raw_text: str) -> list[dict[str, Any]]:
    """Parse one or multiple quick offline lines like 'Xăng 100k', 'Highlands 45k', 'Lương 8.5tr'.

    Returns list of structured transaction dicts ready for preview & SQLite insertion.
    """
    results: list[dict[str, Any]] = []
    lines = [ln.strip() for ln in str(raw_text).splitlines() if ln.strip()]
    for line in lines:
        amt, desc = _parse_amount_from_text(line)
        if amt is None or amt <= 0:
            continue
        low = f" {line.lower()} "
        is_income = line.strip().startswith("+") or any(k in low for k in INCOME_KEYWORDS)
        tx_type = "income" if is_income else "expense"
        tx_date = _detect_date_from_text(line)

        # Clean date string out of description if present
        desc_clean = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]20\d{2}\b", "", desc).strip(" -,:;")
        if not desc_clean:
            desc_clean = "Thu nhập nhanh" if tx_type == "income" else "Chi tiêu tiền mặt"

        cat, conf, method = predict_single_transaction(desc_clean, tx_type)
        results.append(
            {
                "date": tx_date,
                "description": desc_clean,
                "amount": float(amt),
                "type": tx_type,
                "category": cat,
                "confidence": conf,
                "method": method,
                "source_type": "quick_text",
                "transfer_memo": "",
                "ai_note": f"Nhận diện tự động từ ghi chú nhanh ({method}, độ tin cậy {int(round(conf * 100))}%).",
            }
        )
    return results


def parse_bank_notification(
    raw_alert: str,
    monthly_budget: float = 9_500_000,
    api_key: str = "",
) -> dict[str, Any] | None:
    """Parse a Vietnamese bank/e-wallet notification and run AI analysis on transfer content (memo)."""
    text = str(raw_alert).strip()
    if not text:
        return None

    # 1. Detect bank / e-wallet provider
    banks = [
        ("MBBank", ["mbbank", "mb bank", "mb:"]),
        ("Vietcombank", ["vietcombank", "vcb:", "vcb "]),
        ("Techcombank", ["techcombank", "tcb:", "tcb "]),
        ("ACB", ["acb:", "ngan hang acb"]),
        ("TPBank", ["tpbank", "tpb:"]),
        ("VPBank", ["vpbank", "vpb:"]),
        ("BIDV", ["bidv"]),
        ("VietinBank", ["vietinbank", "ctg:"]),
        ("MoMo", ["momo"]),
        ("ZaloPay", ["zalopay"]),
    ]
    bank_name = "Ngân hàng trực tuyến"
    low = text.lower()
    for name, kws in banks:
        if any(k in low for k in kws):
            bank_name = name
            break

    # 2. Detect direction (+ income vs - expense) & signed amount
    tx_type = "expense"
    amount = None
    m_signed = re.search(
        r"(?:^|[\s:(])([+-])\s*(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?\s*(?:tr|triệu|trieu|nghìn|nghin|k)|\d{4,10}\s*(?:vnd|vnđ|đ|d\b))\s*(?:vnd|vnđ|đ|d\b)?",
        text,
        flags=re.IGNORECASE,
    )
    if m_signed:
        sign = m_signed.group(1)
        tx_type = "income" if sign == "+" else "expense"
        amt_parsed, _ = _parse_amount_from_text(m_signed.group(2))
        amount = amt_parsed
    if amount is None:
        m_labeled_amt = re.search(
            r"(?:Số tiền giao dịch|So tien giao dich|Transaction amount|Số tiền|So tien)\s*[:\-]?\s*(?:Transaction amount\s*[:\-]?\s*)?([+-]?\s*\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?\s*(?:tr|triệu|k)|\d{4,10})\s*(?:vnd|vnđ|đ|d)?",
            text,
            flags=re.IGNORECASE,
        )
        if m_labeled_amt:
            amount, _ = _parse_amount_from_text(m_labeled_amt.group(1))
    if amount is None:
        amount, _ = _parse_amount_from_text(text)

    if not m_signed:
        is_explicit_outgoing = any(
            k in low
            for k in (
                "chuyển tiền ngoài", "chuyen tien ngoai", "chuyển tiền trong", "chuyen tien trong",
                "interbank transfer", "tài khoản nguồn", "tai khoan nguon", "debit account",
                "ghi nợ", "ghi no", "thanh toán", "thanh toan", "chuyển thành công", "chuyen thanh cong",
            )
        )
        if not is_explicit_outgoing and any(
            k in low for k in ("ghi có", "ghi co", "nhận tiền", "nhan tien", "chuyển đến", "chuyen den", "cộng ", "lương", "hoàn tiền")
        ):
            tx_type = "income"

    if amount is None or amount <= 0:
        return None

    tx_date = _detect_date_from_text(text)

    # 3. Extract transfer memo (supports single-line SMS and bilingual multi-line bank HTML tables)
    memo = ""
    m_memo = re.search(
        r"\b(?:Nội dung giao dịch|Noi dung giao dich|Nội dung chuyển khoản|Noi dung chuyen khoan|Nội dung chuyển tiền|Noi dung chuyen tien|Transaction remark)\b\s*[:\-]?\s*(?:Transaction remark\s*[:\-]?\s*)?([^\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not m_memo:
        m_memo = re.search(
            r"\b(?:ND|Nội dung|Noi dung|Lời nhắn|Loi nhan|Content)\b\s*[:\-]\s*([^\n]+)",
            text,
            flags=re.IGNORECASE,
        )
    if m_memo:
        memo = m_memo.group(1).strip()
    else:
        memo = text[:140]

    # Clean compact description
    short_desc = f"{bank_name} · {memo[:64]}" if memo else f"Giao dịch {bank_name}"
    cat, conf, method = predict_single_transaction(f"{bank_name} {memo}", tx_type)

    # 4. AI Contextual Analysis of Transfer Content
    budget_pct = (amount / monthly_budget * 100.0) if monthly_budget > 0 else 0.0
    memo_low = memo.lower()

    # Intent tagging
    if tx_type == "income":
        if any(k in memo_low for k in ("luong", "lương", "salary", "thuc tap")):
            intent_tag = "Thu nhập định kỳ (Lương / Thực tập)"
            advice = "Nên trích ngay 20% vào quỹ dự phòng trước khi chi tiêu trong tháng."
        elif any(k in memo_low for k in ("hoan tien", "hoàn tiền", "refund")):
            intent_tag = "Hoàn tiền đơn hàng"
            advice = "Khoản hoàn tiền đã giúp bù đắp lại ngân sách chi tiêu."
        else:
            intent_tag = "Chuyển khoản nhận tiền"
            advice = "Ghi nhận nguồn thu bổ sung — dòng tiền tích lũy tăng tích cực."
    else:
        if any(k in memo_low for k in ("chia tien", "chia tiền", "campuchia", "nhom", "nhóm")):
            intent_tag = "Chia tiền ăn uống / sinh hoạt nhóm"
            advice = "Giao dịch nhóm dễ phát sinh lặp lại cuối tuần — cân nhắc đặt hạn mức đi chơi mỗi tuần."
        elif any(k in memo_low for k in ("phong tro", "phòng trọ", "thue nha", "thuê nhà", "dien nuoc", "điện nước")):
            intent_tag = "Thanh toán hóa đơn cố định định kỳ"
            advice = "Khoản cố định thiết yếu — MoneyLens sẽ tự động đưa vào lịch dự báo chi phí tháng sau."
        elif any(k in memo_low for k in ("shopee", "tiktok", "lazada", "tiki", "don hang", "đơn hàng")):
            intent_tag = "Mua sắm thương mại điện tử"
            advice = "Kiểm tra lại xem món đồ nằm trong kế hoạch hay mua theo cảm hứng flash-sale."
        elif any(k in memo_low for k in ("tra no", "trả nợ", "vay", "muon", "mượn")):
            intent_tag = "Chuyển khoản vay / trả nợ cá nhân"
            advice = "Ghi chú rõ người nhận để tránh nhầm lẫn vào chi tiêu tiêu dùng hàng tháng."
        else:
            intent_tag = f"Thanh toán trực tuyến ({cat})"
            advice = "Đã phân loại tự động và cập nhật vào dòng tiền tháng hiện tại."

    risk_flag = ""
    if tx_type == "expense" and budget_pct >= 25.0:
        risk_flag = f" Cảnh báo: Giao dịch đơn lẻ này chiếm tới {budget_pct:.1f}% ngân sách cả tháng!"

    ai_analysis = (
        f"**Ngân hàng / Ví:** {bank_name} · **Ngữ cảnh:** {intent_tag}. "
        f"Tác động ~{budget_pct:.1f}% ngân sách tháng.{risk_flag} **Gợi ý:** {advice}"
    )

    # Optional LLM deep analysis of transfer memo when API key is configured (accepts AQ., AIza, sk-, gsk_)
    active_key = resolve_saved_api_key(api_key)
    if active_key:
        prompt = (
            f"Phân tích ngắn gọn (2-3 câu tiếng Việt) nội dung chuyển khoản ngân hàng sau:\n"
            f"- Ngân hàng: {bank_name}\n"
            f"- Số tiền: {'+' if tx_type == 'income' else '-'}{int(amount):,} VND (tương đương {budget_pct:.1f}% ngân sách tháng)\n"
            f"- Nội dung chuyển khoản: \"{memo}\"\n"
            f"- Danh mục ML dự đoán: {cat}\n"
            "Hãy chỉ ra: (1) Mục đích giao dịch thực tế, (2) Có dấu hiệu bất thường/rủi ro hoặc lặp lại không, (3) 1 lời khuyên ngắn gọn."
        )
        llm_txt, _ = generate_universal_reply(
            user_message=prompt,
            system_instruction="Bạn là chuyên gia phân tích giao dịch tài chính cá nhân tại Việt Nam.",
            api_key=active_key,
            max_tokens=260,
            temperature=0.3,
        )
        if llm_txt:
            ai_analysis = llm_txt

    ref_code = extract_transaction_reference(text)
    tx_ts = extract_exact_timestamp(text, fallback_date=tx_date)
    counterparty = extract_account_or_counterparty(text)

    return {
        "bank_name": bank_name,
        "date": tx_date,
        "tx_timestamp": tx_ts,
        "reference_code": ref_code,
        "counterparty": counterparty,
        "description": short_desc,
        "amount": float(amount),
        "type": tx_type,
        "category": cat,
        "confidence": conf,
        "method": method,
        "source_type": "bank_sync",
        "transfer_memo": memo,
        "intent_tag": intent_tag,
        "ai_note": ai_analysis,
    }


def _prepare_vision_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Fix EXIF rotation (important for phone photos of handwritten notes/bills) & ensure crisp JPEG/PNG."""
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        # Resize oversized camera images while keeping handwriting crisp (max 1600px)
        max_side = 1600
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, mime_type or "image/jpeg"


def _parse_numeric_amount_safe(raw_val: Any) -> float:
    """Safely parse integer/float/formatted VND amount from Vision JSON."""
    if isinstance(raw_val, (int, float)):
        return abs(float(raw_val))
    s = str(raw_val or "").strip()
    if not s:
        return 0.0
    parsed, _ = _parse_amount_from_text(s)
    if parsed:
        return float(parsed)
    digits = re.sub(r"[^\d]", "", s)
    return float(digits) if digits else 0.0


def parse_bill_image(
    image_bytes: bytes,
    filename: str = "receipt.jpg",
    mime_type: str = "image/jpeg",
    api_key: str = "",
) -> dict[str, Any]:
    """Extract receipt, bank transfer screenshot, or handwritten note via Multimodal Vision AI."""
    active_key = resolve_saved_api_key(api_key)
    today_str = date.today().strftime("%Y-%m-%d")
    vision_err = ""

    if active_key:
        norm_bytes, norm_mime = _prepare_vision_image(image_bytes, mime_type)
        prompt = (
            "Bạn là chuyên gia OCR tài chính đa phương thức tại Việt Nam — đọc chính xác CẢ:\n"
            "1) Biên lai / ảnh chụp chuyển khoản ngân hàng (Agribank, MBBank, Vietcombank, Techcombank, VietinBank, BIDV, ACB, MoMo, ZaloPay...)\n"
            "2) Hóa đơn in siêu thị, quán ăn, quán cà phê, điện nước, dịch vụ\n"
            "3) HÓA ĐƠN / GHI CHÚ CHỮ VIẾT TAY trên giấy (tiếng Việt có dấu hoặc không dấu, viết tắt kiểu 35k, 100k, 1tr2, 50.000đ...)\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "- Trường `amount`: CHỈ lấy TỔNG SỐ TIỀN GIAO DỊCH THỰC TẾ bằng số nguyên dương VND (VD: '357,000 VND' -> 357000; nếu hóa đơn viết tay có nhiều món mà chưa ghi tổng thì tự cộng tổng tất cả các món).\n"
            "- TUYỆT ĐỐI KHÔNG lấy Mã giao dịch (MGD), Số tài khoản (TK), Số điện thoại, Mã hóa đơn hay Barcode làm `amount`.\n"
            "- Trường `merchant`: tên cửa hàng / tên ngân hàng + người thụ hưởng (VD: 'Agribank → NGUYEN THI HANG' hoặc tên quán / tiêu đề ghi chú viết tay).\n"
            "- Trường `transfer_memo`: ghi chính xác 'Nội dung chuyển tiền' trên biên lai ngân hàng HOẶC nội dung chi tiết món/chữ viết tay đọc được.\n"
            "- Trường `handwritten_text`: nếu trong ảnh có CHỮ VIẾT TAY, hãy chép lại đầy đủ từng dòng chữ viết tay đọc được (nếu không có chữ viết tay thì để chuỗi rỗng \"\").\n"
            "- Trường `type`: chỉ dùng 'income' nếu ảnh ghi rõ là NHẬN TIỀN / GHI CÓ / + tiền vào, mặc định là 'expense'.\n"
            "- Trường `date`: định dạng YYYY-MM-DD lấy từ 'Thời gian giao dịch' hoặc ngày trên hóa đơn (VD '22-11-2026' -> '2026-11-22'; nếu không có ngày dùng "
            f"{today_str}).\n\n"
            "Trả về DUY NHẤT một khối JSON hợp lệ đúng cấu trúc sau (không kèm chữ giải thích bên ngoài):\n"
            '{"doc_type": "bank_transfer|printed_receipt|handwritten_note", '
            '"merchant": "tên cửa hàng hoặc ngân hàng → người nhận", '
            '"date": "YYYY-MM-DD", '
            '"amount": 357000, '
            '"type": "expense", '
            '"category": "Food|Shopping|Transport|Bills|Entertainment|Other|Income", '
            '"transfer_memo": "nội dung chuyển tiền hoặc tóm tắt hóa đơn", '
            '"handwritten_text": "toàn bộ nội dung chữ viết tay đọc được nếu có", '
            '"items_summary": "liệt kê ngắn các món / chi tiết chính", '
            '"ai_note": "nhận xét ngắn 1-2 câu bằng tiếng Việt về giao dịch này"}'
        )

        raw_txt, provider_used, vision_err = generate_gemini_vision(
            image_bytes=norm_bytes,
            mime_type=norm_mime,
            prompt=prompt,
            api_key=active_key,
            max_tokens=900,
            temperature=0.1,
        )
        if raw_txt:
            m_json = re.search(r"\{.*\}", raw_txt, flags=re.S)
            if m_json:
                try:
                    data = json.loads(m_json.group(0))
                    merchant = str(data.get("merchant") or "Hóa đơn quét AI").strip()
                    amt = _parse_numeric_amount_safe(data.get("amount"))
                    tx_type = "income" if str(data.get("type", "")).lower() == "income" else "expense"
                    memo = str(data.get("transfer_memo") or "").strip()
                    handwritten = str(data.get("handwritten_text") or "").strip()
                    items = str(data.get("items_summary") or "").strip()
                    doc_type = str(data.get("doc_type") or "printed_receipt").strip()

                    cat = str(data.get("category") or "").strip()
                    if tx_type == "income":
                        cat = "Income"
                    elif cat not in {"Food", "Shopping", "Transport", "Bills", "Entertainment", "Other"}:
                        cat, _, _ = predict_single_transaction(f"{merchant} {memo} {items} {handwritten}", tx_type)

                    raw_dt = str(data.get("date") or "").strip()
                    tx_date = _detect_date_from_text(raw_dt) if raw_dt else today_str

                    combined_memo = memo
                    if handwritten and handwritten.lower() not in combined_memo.lower():
                        combined_memo = f"{combined_memo}\n[Chữ viết tay]: {handwritten}".strip() if combined_memo else handwritten
                    if not combined_memo and items:
                        combined_memo = items

                    desc = merchant
                    if items and doc_type != "bank_transfer" and items.lower() not in merchant.lower():
                        desc = f"{merchant} ({items[:45]})"

                    note_prefix = f"[{provider_used}] " if provider_used else ""
                    ai_note = note_prefix + str(
                        data.get("ai_note") or "Đã trích xuất tự động từ ảnh hóa đơn / chữ viết tay bằng AI Vision."
                    )
                    return {
                        "used_vision_ai": True,
                        "doc_type": doc_type,
                        "date": tx_date,
                        "description": desc,
                        "amount": amt if amt > 0 else 50_000.0,
                        "type": tx_type,
                        "category": cat,
                        "confidence": 0.97,
                        "source_type": "bill_ocr",
                        "transfer_memo": combined_memo,
                        "handwritten_text": handwritten,
                        "ai_note": ai_note,
                    }
                except Exception as exc:
                    vision_err = f"Lỗi đọc JSON từ AI Vision: {exc}"

    # Safe fallback: NEVER extract random long numeric Zalo/Facebook image IDs as VND amounts or descriptions!
    clean_name = re.sub(r"\.[a-zA-Z0-9]+$", "", str(filename)).replace("_", " ").replace("-", " ").strip()
    looks_like_random_id = bool(re.search(r"\d{8,}", clean_name)) or (
        sum(ch.isdigit() for ch in clean_name) > max(len(clean_name) * 0.45, 6)
    )
    if looks_like_random_id or not clean_name or clean_name.lower() in {"receipt", "bill", "image", "photo", "img", "capture"}:
        desc_guess = "Hóa đơn / Biên lai (nhập lại thủ công)"
        amt_guess = None
    else:
        amt_guess, desc_guess = _parse_amount_from_text(clean_name)
        if amt_guess and amt_guess > 500_000_000:
            amt_guess = None
        if not desc_guess:
            desc_guess = "Hóa đơn / Biên lai"

    cat, conf, _ = predict_single_transaction(desc_guess, "expense")
    err_detail = f" (Chi tiết: {vision_err})" if vision_err else ""
    fallback_note = (
        f"Không gọi được AI Vision{err_detail}. Bạn hãy kiểm tra API Key ở mục **AI API Key** góc dưới bên trái hoặc chỉnh nhanh số tiền & nội dung bên dưới trước khi lưu."
        if active_key
        else "Chế độ xem trước offline (chưa nhập API Key). Dán Google API Key (bắt đầu bằng `AQ.` hoặc `AIza...`) ở mục **AI API Key** bên dưới để AI đọc tự động hóa đơn in, biên lai ngân hàng & chữ viết tay!"
    )

    return {
        "used_vision_ai": False,
        "doc_type": "unknown",
        "date": today_str,
        "description": desc_guess,
        "amount": float(amt_guess) if amt_guess else 50_000.0,
        "type": "expense",
        "category": cat,
        "confidence": conf,
        "source_type": "bill_ocr",
        "transfer_memo": "",
        "handwritten_text": "",
        "ai_note": fallback_note,
    }
