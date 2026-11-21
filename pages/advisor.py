"""Trang Cố vấn Tài chính AI (AI Advisor).
Giao diện hội thoại tương tác trực tiếp với mô hình Gemini AI để nhận tư vấn tài chính.
"""

from __future__ import annotations

import sys
from pathlib import Path
import streamlit as st

# Setup sys.path to import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing import load_and_clean_data
from src.categorization import categorize_transactions
from src.analysis import get_overview_metrics
from src.forecasting import forecast_balance
from src.ai_advisor import ask_advisor

st.set_page_config(page_title="AI Advisor | MoneyLens-AI", page_icon="🤖", layout="wide")


def ensure_data():
    """Ensure session state contains cleaned data, fallback to sample CSV."""
    if "df" not in st.session_state or st.session_state["df"] is None or st.session_state["df"].empty:
        sample_path = PROJECT_ROOT / "data" / "sample_transactions.csv"
        raw_df = load_and_clean_data(sample_path)
        st.session_state["df"] = categorize_transactions(raw_df)
        st.session_state["data_source"] = "Tự động nạp mẫu (sample_transactions.csv)"


ensure_data()
df = st.session_state["df"]

st.title("🤖 MoneyLens AI Advisor")
st.caption(
    "Trợ lý thông minh phân tích bức tranh tài chính và đưa ra lời khuyên cá nhân hóa bằng Gemini API."
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "👋 Xin chào! Tôi là **MoneyLens AI**, trợ lý tài chính cá nhân của bạn.\n\n"
                "Tôi đã đọc và tổng hợp toàn bộ lịch sử thu chi cùng dự báo số dư của bạn. "
                "Bạn có thể hỏi tôi bất kỳ điều gì, ví dụ:\n"
                "- *'Dựa trên chi tiêu hiện tại, tôi nên cắt giảm khoản nào?'*\n"
                "- *'Tháng này tôi có nguy cơ thâm hụt tiền trọ không?'*\n"
                "- *'Làm sao để người mới đi làm tiết kiệm được 20% lương?'*"
            ),
        }
    ]

# Render existing chat messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Chat Input
user_query = st.chat_input("Nhập câu hỏi tài chính của bạn tại đây...")

if user_query:
    # 1. Append and display user message
    st.session_state["messages"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # 2. Compute current metrics & forecast context
    metrics = get_overview_metrics(df)
    forecast = forecast_balance(df, days_ahead=30, monthly_budget=5000000.0)

    # 3. Call AI Advisor
    with st.chat_message("assistant"):
        with st.spinner("MoneyLens AI đang phân tích dữ liệu và suy nghĩ câu trả lời..."):
            response_text = ask_advisor(
                question=user_query,
                df=df,
                metrics=metrics,
                forecast=forecast,
            )
            st.markdown(response_text)

    # 4. Append assistant response to history
    st.session_state["messages"].append({"role": "assistant", "content": response_text})

# Sidebar quick prompts
with st.sidebar:
    st.subheader("💡 Câu hỏi gợi ý:")
    quick_prompts = [
        "Phân tích top các khoản chi tốn tiền nhất của tôi?",
        "Tư vấn kế hoạch phân bổ thu nhập 50/30/20 phù hợp?",
        "Tôi có các khoản phí định kỳ nào cần lưu ý?",
        "Làm sao để sinh viên hạn chế chi tiêu cà phê trà sữa?",
    ]
    for prompt in quick_prompts:
        if st.button(prompt, use_container_width=True):
            st.session_state["messages"].append({"role": "user", "content": prompt})
            metrics = get_overview_metrics(df)
            forecast = forecast_balance(df, days_ahead=30)
            answer = ask_advisor(prompt, df, metrics, forecast)
            st.session_state["messages"].append({"role": "assistant", "content": answer})
            st.rerun()
