"""Product Knowledge Base & Floating Circular AI Help Widget Engine (MoneyLens AI).

Knows every screen, feature, input syntax, legal bank sync approach, Dark/Light mode,
VI/EN language switcher, and account workflow in MoneyLens AI — ensuring accurate answers
in both Vietnamese and English (powered by Gemini 2.5 Flash when API key is configured,
with instant deterministic bilingual fallback offline).
"""

from __future__ import annotations

import os
from typing import Any

from src.llm_client import generate_universal_reply

APP_MANUAL_CONTEXT = """
HƯỚNG DẪN VẬN HÀNH CHÍNH THỨC CỦA MONEYLENS AI:
1. BỐ CỤC GIAO DIỆN:
   - Thanh Header trên cùng màu xanh đen đậm trải kín 2 bên: Logo MoneyLens AI bên trái; bên phải gồm nút đổi ngôn ngữ (VI / EN), nút bật/tắt Dark / Light Mode, hồ sơ tên tài khoản Google đang đăng nhập, nút Hồ sơ và Đăng xuất.
   - Thanh Sub-navigation ngang: Chuyển 4 màn hình chính:
     (1) Tổng quan tài chính (Overview — có bảng giao dịch và tính năng Xóa giao dịch nhập nhầm)
     (2) Phân tích chi tiêu (Spending Insights — có tính năng Thêm & Xóa khoản chi tiêu cố định hàng tháng)
     (3) Dự báo tài chính (Financial Forecast & What-If)
     (4) Trợ lý AI Advisor (trả lời mọi câu hỏi như ChatGPT/Gemini kèm ngữ cảnh tài chính cá nhân)
   - Khung bên trái (Ghi chép & Đồng bộ AI — KHÔNG dùng file CSV):
     • Tab "Nhập nhanh": Gõ câu ngắn như "Xăng 100k", "Highlands 45k", "Nhận lương 8.5tr".
     • Tab "Chụp Bill": Tải ảnh hoặc chụp camera để AI OCR bóc tách hóa đơn.
     • Tab "Bank Sync": Bật nhận biến động số dư qua **Email ngân hàng (Gmail IMAP + App Password)** → Tự động quét ngay lập tức email mới từ ngân hàng → AI bóc tách dữ liệu → Tự đẩy vào bảng giao dịch! Ngoài ra vẫn hỗ trợ cổng Webhook chỉ-đọc SePay / Casso / PayOS.
2. ĐĂNG NHẬP GOOGLE & DỮ LIỆU TRẮNG TINH CHO NGƯỜI DÙNG MỚI:
   - Người dùng đăng nhập bằng tài khoản Google. Thông tin tên, hồ sơ và phiên đăng nhập được lưu vĩnh viễn trong SQLite (đăng nhập lại cùng 1 Gmail không phải nhập lại tên).
   - Tài khoản mới bắt đầu trắng tinh (0 giao dịch), chỉ lưu dữ liệu khi người dùng tự thêm, chụp bill, bật đồng bộ Email ngân hàng hoặc thêm khoản chi cố định.
3. THÊM / XÓA GIAO DỊCH & CHI TIÊU CỐ ĐỊNH:
   - Xóa giao dịch nhập nhầm: ngay dưới bảng "Giao dịch gần đây" ở trang Tổng quan tài chính.
   - Thêm / Xóa khoản chi tiêu cố định hàng tháng (tiền trọ, điện nước, Wifi, Spotify, Netflix...): trong thẻ "Chi tiêu định kỳ & Khoản cố định" ở trang Phân tích chi tiêu.
"""


def answer_help_question(
    question: str,
    lang: str = "vi",
    api_key: str = "",
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Answer ANY question (both MoneyLens AI guidance and general ChatGPT/Gemini-like queries)."""
    q = str(question).strip()
    if not q:
        return "Hãy nhập câu hỏi bất kỳ của bạn!" if lang == "vi" else "Ask me anything!"

    lang_inst = (
        "Trả lời bằng ngôn ngữ của câu hỏi người dùng (mặc định Tiếng Việt tự nhiên, rõ ràng, súc tích, dễ hiểu)."
        if lang == "vi"
        else "Reply in the user's language (default clear, friendly English)."
    )
    system_instruction = (
        "Bạn là trợ lý AI toàn năng tích hợp trong MoneyLens AI (tương tự ChatGPT / Gemini).\n"
        "- Bạn có thể trả lời TẤT CẢ mọi câu hỏi thuộc mọi lĩnh vực (tài chính, học tập, lập trình, đời sống, kiến thức chung, viết lách, tính toán...) — KHÔNG bị giới hạn chỉ trong hướng dẫn web.\n"
        "- Khi người dùng hỏi về cách dùng hoặc tính năng của web MoneyLens AI, hãy trả lời chính xác 100% theo tài liệu vận hành bên dưới.\n"
        f"- {lang_inst}\n\n"
        f"{APP_MANUAL_CONTEXT}"
    )

    llm_reply, llm_src = generate_universal_reply(
        user_message=q,
        system_instruction=system_instruction,
        history=history,
        api_key=api_key,
        max_tokens=700,
        temperature=0.55,
    )
    if llm_reply:
        return llm_reply
    if llm_src == "RATE_LIMIT_402" and not any(
        k in q.lower()
        for k in ("xăng", "bill", "ngân hàng", "bank", "đăng nhập", "google", "dark", "light", "dự báo", "what-if", "moneylens")
    ):
        return (
            "Cổng AI miễn phí không cần key tạm chạm giới hạn 1 câu/45 giây. Bạn chờ ~30 giây rồi gửi lại, hoặc dán **Gemini API Key miễn phí** vào mục **AI API Key** ở góc dưới bên trái để hỏi mọi câu hỏi không giới hạn!"
            if lang == "vi"
            else "The zero-key AI endpoint hit its 1 reply / 45s cooldown. Retry in ~30s, or paste a free Gemini / Groq / OpenAI API key under **AI API Key** (bottom-left) for unlimited replies!"
        )

    low = q.lower()

    # Bilingual deterministic exact product help matcher
    if any(k in low for k in ("xăng", "100k", "nhập nhanh", "bill", "ảnh", "chụp", "hóa đơn", "ocr", "offline", "csv", "text", "receipt", "photo")):
        if lang == "en":
            return (
                "**Quick Offline Entry & Bill OCR (No CSV needed):**\n"
                "1. On the left **AI Capture** panel, pick **Quick Text** and type e.g. `Gas 100k`, `Highlands 45k`, or `Salary 8.5tr` (multi-line supported). ML auto-categorizes and saves to your account.\n"
                "2. Pick **Scan Bill** to upload/photograph a receipt — Gemini 2.5 Flash Vision extracts merchant, date, total & category (or edit & confirm offline)."
            )
        return (
            "**Cách nhập chi tiêu offline & quét ảnh hóa đơn (không dùng CSV):**\n"
            "1. Ở khung **Ghi chép & Đồng bộ AI** bên trái, chọn tab **Nhập nhanh** → gõ `Xăng 100k`, `Highlands 45k` hoặc `Nhận lương 8.5tr` (có thể gõ nhiều dòng). AI tự tách tiền và phân loại vào 6 danh mục.\n"
            "2. Chọn tab **Chụp ảnh Bill** → tải ảnh hoặc chụp trực tiếp hóa đơn để Gemini Vision đọc cửa hàng & số tiền (hoặc xác nhận nhanh ở chế độ offline)."
        )

    if any(k in low for k in ("ngân hàng", "bank", "api", "phạm pháp", "hợp pháp", "chuyển khoản", "sms", "webhook", "momo", "casso", "sepay", "payos", "legal", "auto")):
        if lang == "en":
            return (
                "**100% Legal Real-Time Bank Auto-Sync:**\n"
                "- MoneyLens AI runs a live **Webhook Receiver (Port 8502)** and auto-refreshes every 4 seconds when new transactions arrive — zero bank passwords!\n"
                "- Supported legal channels in **Bank Sync**: **SePay.vn**, **Casso.vn**, **PayOS** read-only webhooks, plus **SMS / Email / iOS Shortcuts / Android MacroDroid / Gmail Forwarding**.\n"
                "- Open the **Bank Sync** tab to copy your personal Webhook URL or click **Trigger Real Live Webhook** to watch the dashboard update automatically!"
            )
        return (
            "**Đồng bộ ngân hàng tự động hợp pháp 100% (Auto-Update Real-Time):**\n"
            "- MoneyLens AI tích hợp sẵn **Webhook Receiver (Port 8502)** chạy ngầm và tự động cập nhật biểu đồ/KPI mỗi 4 giây khi có giao dịch mới — tuyệt đối không cần mật khẩu ngân hàng!\n"
            "- Hỗ trợ đủ 4 kênh hợp pháp trong tab **Bank Sync**: cổng chỉ-đọc **SePay.vn**, **Casso.vn**, **PayOS** và **SMS / Email / iOS Shortcuts / Android MacroDroid / Gmail Forwarding**.\n"
            "- Vào tab **Bank Sync** bên trái để lấy Webhook URL cá nhân hoặc bấm **Gửi thử giao dịch Webhook thật** xem web tự cập nhật ngay lập tức!"
        )

    if any(k in low for k in ("đăng nhập", "đăng ký", "tài khoản", "mật khẩu", "google", "hồ sơ", "onboarding", "login", "register", "account", "password")):
        if lang == "en":
            return (
                "**Google Sign-In & Personal Onboarding:**\n"
                "- Sign in with your own Google email (supports live Google OAuth 2.0 via `.env` and instant local Google sign-in).\n"
                "- On first login, MoneyLens AI prompts for your **Full Name**, role, monthly income, budget target & goal — then displays your own name & isolated data.\n"
                "- Click **Profile** or **Sign Out** in the top-right bar anytime to edit your profile or switch Google accounts."
            )
        return (
            "**Đăng nhập Google & Thiết lập hồ sơ cá nhân:**\n"
            "- Bạn đăng nhập trực tiếp bằng **tài khoản Google** (mỗi tài khoản hoàn toàn tách biệt dữ liệu và tên hiển thị riêng).\n"
            "- Lần đầu đăng nhập, web sẽ hỏi **Họ và tên** cùng các thông tin tài chính cơ bản (nghề nghiệp, thu nhập, ngân sách, mục tiêu) rồi mới vào trang chính.\n"
            "- Bạn có thể bấm nút **Hồ sơ** hoặc **Đăng xuất** ở thanh trên cùng bất cứ lúc nào để sửa thông tin hoặc đổi tài khoản Google."
        )

    if any(k in low for k in ("dark", "light", "giao diện tối", "giao diện sáng", "ngôn ngữ", "tiếng anh", "language", "theme", "dark mode", "light mode")):
        if lang == "en":
            return (
                "**Dark/Light Mode & Language Switcher:**\n"
                "- Look at the top-right dark header bar: click the **VI / EN** button to switch language instantly, and click **Dark / Light** to toggle theme across all cards and Plotly charts!"
            )
        return (
            "**Bật Dark/Light Mode & Đổi ngôn ngữ VI/EN:**\n"
            "- Ngay trên thanh Header xanh đen trên cùng (góc phải): nhấn nút **VI / EN** để đổi ngôn ngữ toàn web, và nhấn nút **Sáng / Tối** để chuyển giao diện Dark/Light Mode (cả thẻ lẫn biểu đồ tự đổi màu theo)."
        )

    if any(k in low for k in ("dự báo", "laptop", "what-if", "forecast", "pdf", "báo cáo", "xuất", "gemini", "api key")):
        if lang == "en":
            return (
                "**Forecast, PDF Export & Gemini API Key:**\n"
                "- Open **Financial Forecast** in the top nav to see Statsmodels 30-day projections and test **Save** or **Buy 15M Laptop** presets.\n"
                "- Click **Export Report** on Overview to download a print-ready PDF/HTML financial summary.\n"
                "- Add a free **Gemini API Key** inside the left panel's *AI Settings* expander to unlock live Gemini 2.5 Flash Vision OCR and free-form LLM chat."
            )
        return (
            "**Dự báo What-If, Xuất báo cáo & Gemini API Key:**\n"
            "- Vào tab **Dự báo tài chính** trên thanh menu ngang để xem dự báo 30 ngày (Statsmodels SES) và bấm thử kịch bản **Tiết kiệm** hoặc **Mua Laptop 15tr**.\n"
            "- Bấm **Xuất báo cáo (PDF)** ở góc phải màn hình Tổng quan để tải báo cáo in ra PDF.\n"
            "- Muốn bật đọc ảnh hóa đơn Vision & chat LLM tự do: mở mục **Cấu hình Gemini API** ở góc dưới bên trái và dán API Key (miễn phí tại AI Studio)."
        )

    if lang == "en":
        return (
            "I'm the **MoneyLens AI Guide**! You can ask me about:\n"
            "- Quick text entry (`Gas 100k`) & Bill Photo OCR\n"
            "- Legal Bank Transfer Sync & AI memo analysis\n"
            "- Login / Register & user data isolation\n"
            "- Dark/Light Mode, VI/EN switcher, Forecast What-If & Report Export"
        )
    return (
        "Mình là **Trợ lý hướng dẫn MoneyLens AI**! Bạn có thể hỏi mình về:\n"
        "- Cách đăng nhập **Google**, thiết lập hồ sơ cá nhân lần đầu & đổi tài khoản\n"
        "- Cách bật **Auto-Sync Webhook** hợp pháp (**SePay / Casso / PayOS / SMS-Email Forwarding**)\n"
        "- Cách nhập nhanh (`Xăng 100k`) & chụp ảnh hóa đơn Bill OCR\n"
        "- Bật Dark/Light mode, đổi ngôn ngữ VI/EN, mô phỏng mua Laptop 15tr & xuất báo cáo PDF"
    )
