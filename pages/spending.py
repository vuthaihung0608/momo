"""Trang Phân tích Chi tiêu (Spending).
Hiển thị cơ cấu chi tiêu theo danh mục, cảnh báo bất thường và danh mục chi tiêu định kỳ.
"""

from __future__ import annotations

import sys
from pathlib import Path
import plotly.express as px
import streamlit as st

# Setup sys.path to import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing import load_and_clean_data
from src.categorization import categorize_transactions, detect_recurring_transactions
from src.analysis import get_spending_by_category, detect_anomalies

st.set_page_config(page_title="Phân Tích Chi Tiêu | MoneyLens-AI", page_icon="🛒", layout="wide")


def ensure_data():
    """Ensure session state contains cleaned data, fallback to sample CSV."""
    if "df" not in st.session_state or st.session_state["df"] is None or st.session_state["df"].empty:
        sample_path = PROJECT_ROOT / "data" / "sample_transactions.csv"
        raw_df = load_and_clean_data(sample_path)
        st.session_state["df"] = categorize_transactions(raw_df)
        st.session_state["data_source"] = "Tự động nạp mẫu (sample_transactions.csv)"


ensure_data()
df = st.session_state["df"]

st.title("🛒 Phân Tích Cơ Cấu Chi Tiêu")
st.caption(f"Dữ liệu đang dùng: {st.session_state.get('data_source', 'Không rõ')}")

# 1. Category Distribution
st.subheader("🍕 1. Tỷ Trọng Chi Tiêu Theo Danh Mục")

spending_df = get_spending_by_category(df)

if not spending_df.empty:
    col_chart, col_table = st.columns([1.2, 1], gap="medium")

    with col_chart:
        fig_pie = px.pie(
            spending_df,
            names="category",
            values="amount",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe,
            title="Biểu đồ phân bổ chi tiêu",
        )
        fig_pie.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hoverinfo="label+value+percent",
        )
        fig_pie.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=380)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_table:
        st.write("**Bảng xếp hạng chi tiêu:**")
        st.dataframe(
            spending_df.style.format({
                "amount": "{:,.0f} VND",
                "percentage": "{:.1f}%",
            }),
            use_container_width=True,
            height=340,
        )
else:
    st.info("Chưa có giao dịch chi tiêu (expense) nào trong tập dữ liệu.")

st.divider()

# 2. Anomalous Transactions Detection
st.subheader("🚨 2. Phát Hiện Giao Dịch Chi Tiêu Bất Thường")
st.write(
    "Hệ thống tự động phát hiện các khoản chi cao vượt mức bình quân cộng 2 lần độ lệch chuẩn "
    "`(mean + 2 * std)`. Đây có thể là các khoản mua sắm bốc đồng hoặc chi phí đột xuất."
)

anomalies_df = detect_anomalies(df)

if not anomalies_df.empty:
    st.warning(f"⚠️ Phát hiện **{len(anomalies_df)}** giao dịch có mức chi bất thường vượt ngưỡng!")
    st.dataframe(
        anomalies_df.style.format({
            "amount": "{:,.0f} VND",
            "deviation_score": "{:.2f} σ",
            "date": lambda d: d.strftime("%Y-%m-%d"),
        }),
        use_container_width=True,
    )
else:
    st.success("✅ Tuyệt vời! Không phát hiện giao dịch chi tiêu bất thường nào vượt ngưỡng rủi ro.")

st.divider()

# 3. Recurring Transactions
st.subheader("🔄 3. Giao Dịch Lặp Lại Định Kỳ (Subscriptions & Fixed Costs)")
st.write(
    "Các khoản chi xuất hiện nhiều lần (tiền phòng trọ, điện nước, internet, gói Netflix/Spotify, cà phê cố định...)."
)

recurring_df = detect_recurring_transactions(df)

if not recurring_df.empty:
    total_recurring = recurring_df["total_amount"].sum()
    st.info(f"💡 Tổng số tiền cho các khoản định kỳ/lặp lại: **{total_recurring:,.0f} VND**")
    st.dataframe(
        recurring_df.style.format({
            "amount": "{:,.0f} VND",
            "total_amount": "{:,.0f} VND",
        }),
        use_container_width=True,
    )
else:
    st.write("Chưa ghi nhận đủ số lần lặp lại để xác định khoản chi định kỳ.")
