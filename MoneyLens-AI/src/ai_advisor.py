"""Module: ai_advisor.py
Owner: Member 3

Provides financial advice generation powered by the Google GenAI (Gemini) API.
Includes a structured context builder and an offline mock fallback mode
for test execution and environments without an active API key.
"""

from __future__ import annotations

import os
from typing import Any
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()


def build_financial_context(
    df: pd.DataFrame,
    metrics: dict[str, float],
    forecast: dict[str, Any],
) -> str:
    """Format transaction summaries and forecast data into a concise text prompt context.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with categories and amounts.
    metrics : dict[str, float]
        Summary metrics {'total_income', 'total_expense', 'current_balance'}.
    forecast : dict[str, Any]
        Forecast dictionary with projected balance and risk flags.

    Returns
    -------
    str
        Structured context string describing the user's current financial situation.
    """
    total_income = metrics.get("total_income", 0.0)
    total_expense = metrics.get("total_expense", 0.0)
    current_balance = metrics.get("current_balance", 0.0)
    projected_balance = forecast.get("projected_balance", 0.0)
    expected_expense = forecast.get("expected_expense", 0.0)
    over_budget_risk = forecast.get("over_budget_risk", False)

    # Top spending categories summary
    top_categories_str = "Không có dữ liệu chi tiêu"
    if not df.empty and "category" in df.columns and "type" in df.columns:
        expenses = df[df["type"] == "expense"]
        if not expenses.empty:
            cat_summary = (
                expenses.groupby("category")["amount"]
                .sum()
                .sort_values(ascending=False)
                .head(5)
            )
            top_categories_str = ", ".join(
                f"{cat}: {amt:,.0f} VND" for cat, amt in cat_summary.items()
            )

    risk_status_str = "Có nguy cơ thâm hụt / vượt ngân sách ⚠️" if over_budget_risk else "Ngân sách an toàn ✅"

    context = f"""[HỒ SƠ TÀI CHÍNH CÁ NHÂN CỦA NGƯỜI DÙNG]
- Tổng thu nhập ghi nhận: {total_income:,.0f} VND
- Tổng chi tiêu ghi nhận: {total_expense:,.0f} VND
- Số dư hiện tại: {current_balance:,.0f} VND
- Dự kiến chi tiêu 30 ngày tới: {expected_expense:,.0f} VND
- Số dư ước tính sau 30 ngày: {projected_balance:,.0f} VND
- Trạng thái rủi ro tài chính: {risk_status_str}
- Top 5 danh mục chi tiêu cao nhất: {top_categories_str}
"""
    return context.strip()


def _generate_mock_advice(
    question: str,
    metrics: dict[str, float],
    forecast: dict[str, Any],
) -> str:
    """Generate a high-quality baseline response when GEMINI_API_KEY is not configured."""
    total_income = metrics.get("total_income", 0.0)
    total_expense = metrics.get("total_expense", 0.0)
    current_balance = metrics.get("current_balance", 0.0)
    projected_balance = forecast.get("projected_balance", 0.0)
    over_budget = forecast.get("over_budget_risk", False)

    savings_rate = (
        (current_balance / total_income * 100) if total_income > 0 else 0.0
    )

    advice = f"""🤖 **[MoneyLens AI Advisor - Chế độ Trợ lý Baseline]**

Chào bạn! Hệ thống hiện đang chạy ở chế độ **Offline Baseline** (chưa phát hiện `GEMINI_API_KEY` hợp lệ trong file `.env`). Dưới đây là phân tích tự động dựa trên số liệu của bạn:

### 📊 Bức tranh tài chính tóm tắt:
- **Tổng thu:** {total_income:,.0f} VND
- **Tổng chi:** {total_expense:,.0f} VND
- **Số dư hiện tại:** {current_balance:,.0f} VND (Tỷ lệ tiết kiệm: {savings_rate:.1f}%)
- **Dự báo 30 ngày:** Số dư còn khoảng **{projected_balance:,.0f} VND**
- **Cảnh báo ngân sách:** {'⚠️ **CẢNH BÁO:** Bạn có nguy cơ thâm hụt hoặc vượt ngân sách!' if over_budget else '✅ Tình hình chi tiêu đang trong tầm kiểm soát.'}

### 💡 Lời khuyên cho câu hỏi: *"{question}"*
1. **Áp dụng quy tắc 50/30/20:** Hãy phân bổ 50% thu nhập cho chi phí thiết yếu (tiền trọ, ăn uống, xăng xe), 30% cho nhu cầu cá nhân/giải trí, và dành tối thiểu 20% cho quỹ tiết kiệm khẩn cấp.
2. **Kiểm soát khoản chi nhỏ lặp lại (Latte Factor):** Cà phê, trà sữa hay đặt đồ ăn vặt hàng ngày có thể tích tụ thành số tiền lớn mỗi tháng.
3. **Theo dõi đều đặn:** Cập nhật thu chi mỗi tuần và rà soát các giao dịch bất thường để không bị động vào cuối tháng.

*(💡 **Gợi ý:** Để kích hoạt phản hồi thông minh đầy đủ từ mô hình Gemini 2.5 Flash, bạn hãy mở file `.env` và điền khóa `GEMINI_API_KEY=...` của mình nhé!)*
"""
    return advice.strip()


def ask_advisor(
    question: str,
    df: pd.DataFrame,
    metrics: dict[str, float],
    forecast: dict[str, Any],
) -> str:
    """Query the AI Financial Advisor with financial context and user question.

    If GEMINI_API_KEY is available, connects to the official Google GenAI API.
    Otherwise, falls back gracefully to structured baseline mock advice.

    Parameters
    ----------
    question : str
        The financial question or inquiry asked by the user.
    df : pd.DataFrame
        Cleaned transactions DataFrame.
    metrics : dict[str, float]
        Dictionary of overview metrics.
    forecast : dict[str, Any]
        Dictionary of forecast predictions.

    Returns
    -------
    str
        Markdown-formatted advice string from the AI Advisor.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # Fallback to mock if API key is not provided or placeholder
    if not api_key or api_key in ["your_api_key_here", "your_gemini_api_key_here"]:
        return _generate_mock_advice(question, metrics, forecast)

    # Use Google GenAI API when key is configured
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        context = build_financial_context(df, metrics, forecast)

        prompt = f"""Bạn là MoneyLens AI - Cố vấn tài chính cá nhân thông minh và tận tâm dành cho sinh viên và người trẻ mới đi làm tại Việt Nam.
Phong cách giao tiếp: Gần gũi, súc tích, thực tế, dùng tiếng Việt chuẩn, đưa ra lời khuyên có tính hành động cao (actionable advice).

Dưới đây là dữ liệu tài chính thực tế của người dùng:
{context}

Câu hỏi của người dùng:
"{question}"

Hãy phân tích và đưa ra câu trả lời chi tiết, thực tế, kèm các bước hành động cụ thể để tối ưu hóa tài chính."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip()
        return _generate_mock_advice(question, metrics, forecast)

    except Exception as exc:
        # Graceful fallback on network/quota/authentication error
        mock_output = _generate_mock_advice(question, metrics, forecast)
        return (
            f"> ⚠️ *Không thể kết nối trực tiếp đến Gemini API ({exc}). Đang hiển thị kết quả từ hệ thống phân tích nội bộ:*\n\n"
            + mock_output
        )

    # TODO (Member 3): Nâng cấp AI Advisor với bộ nhớ hội thoại nhiều lượt (ConversationBufferMemory),
    # RAG truy xuất tài liệu quản lý tài chính cá nhân, và tích hợp Function Calling
    # để cho phép Gemini tự động truy vấn dữ liệu từ SQLite/Pandas.


if __name__ == "__main__":
    print("=== Testing src.ai_advisor ===")
    mock_df = pd.DataFrame({
        "date": pd.to_datetime(["2026-11-01", "2026-11-02"]),
        "description": ["Lương", "Tiền trọ"],
        "amount": [6000000.0, 2500000.0],
        "type": ["income", "expense"],
        "category": ["Salary", "Housing"],
    })
    mock_metrics = {"total_income": 6000000.0, "total_expense": 2500000.0, "current_balance": 3500000.0}
    mock_forecast = {"projected_balance": 1500000.0, "expected_expense": 2000000.0, "over_budget_risk": False}

    ctx = build_financial_context(mock_df, mock_metrics, mock_forecast)
    print("Built Financial Context:")
    print(ctx)

    advice = ask_advisor("Tôi có nên mua thêm laptop mới không?", mock_df, mock_metrics, mock_forecast)
    print("\nAI Advisor Response (Baseline Mock):")
    print(advice)
    assert len(advice) > 50, "Advice response should not be empty"
    print("\n[PASS] src.ai_advisor self-test completed successfully!")
