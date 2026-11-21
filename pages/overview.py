"""Trang Tổng quan tài chính (Overview).
Hiển thị các chỉ số cốt lõi và biểu đồ dòng tiền theo thời gian.
"""

from __future__ import annotations

import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup sys.path to import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing import load_and_clean_data
from src.categorization import categorize_transactions
from src.analysis import get_overview_metrics, get_cashflow_over_time

# Page config
st.set_page_config(page_title="Tổng Quan Tài Chính | MoneyLens-AI", page_icon="📊", layout="wide")


def ensure_data():
    """Ensure session state contains cleaned data, fallback to sample CSV."""
    if "df" not in st.session_state or st.session_state["df"] is None or st.session_state["df"].empty:
        sample_path = PROJECT_ROOT / "data" / "sample_transactions.csv"
        raw_df = load_and_clean_data(sample_path)
        st.session_state["df"] = categorize_transactions(raw_df)
        st.session_state["data_source"] = "Tự động nạp mẫu (sample_transactions.csv)"


ensure_data()
df = st.session_state["df"]

st.title("📊 Tổng Quan Tài Chính")
st.caption(f"Dữ liệu đang dùng: {st.session_state.get('data_source', 'Không rõ')}")

# 1. Overview Metrics
metrics = get_overview_metrics(df)

m1, m2, m3 = st.columns(3)
m1.metric(
    label="💚 Tổng Thu Nhập (Income)",
    value=f"{metrics['total_income']:,.0f} VND",
    delta=None,
)
m2.metric(
    label="❤️ Tổng Chi Tiêu (Expense)",
    value=f"{metrics['total_expense']:,.0f} VND",
    delta=None,
    delta_color="inverse",
)
m3.metric(
    label="💎 Số Dư Hiện Tại (Balance)",
    value=f"{metrics['current_balance']:,.0f} VND",
    delta=f"{((metrics['current_balance'] / metrics['total_income'] * 100) if metrics['total_income'] > 0 else 0):.1f}% tích lũy",
)

st.divider()

# 2. Cashflow Over Time Chart
st.subheader("📈 Diễn Biến Dòng Tiền & Số Dư Lũy Kế")

cashflow_df = get_cashflow_over_time(df)

if not cashflow_df.empty:
    fig = go.Figure()

    # Bar chart for Daily Income
    fig.add_trace(
        go.Bar(
            x=cashflow_df["date"],
            y=cashflow_df["income"],
            name="Thu Nhập Theo Ngày",
            marker_color="#22c55e",
            opacity=0.7,
        )
    )

    # Bar chart for Daily Expense
    fig.add_trace(
        go.Bar(
            x=cashflow_df["date"],
            y=cashflow_df["expense"],
            name="Chi Tiêu Theo Ngày",
            marker_color="#ef4444",
            opacity=0.7,
        )
    )

    # Line chart for Cumulative Balance
    fig.add_trace(
        go.Scatter(
            x=cashflow_df["date"],
            y=cashflow_df["cumulative_balance"],
            name="Số Dư Lũy Kế",
            mode="lines+markers",
            line=dict(color="#3b82f6", width=3),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="Dòng Tiền Thu/Chi Hằng Ngày và Đường Tăng Trưởng Số Dư",
        xaxis_title="Ngày Giao Dịch",
        yaxis=dict(title="Số tiền phát sinh (VND)"),
        yaxis2=dict(
            title="Số dư lũy kế (VND)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        height=450,
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Chi tiết bảng dòng tiền theo ngày"):
        st.dataframe(
            cashflow_df.style.format({
                "income": "{:,.0f} VND",
                "expense": "{:,.0f} VND",
                "net_cashflow": "{:,.0f} VND",
                "cumulative_balance": "{:,.0f} VND",
                "date": lambda d: d.strftime("%Y-%m-%d"),
            }),
            use_container_width=True,
        )
else:
    st.warning("Chưa có đủ dữ liệu để tổng hợp dòng tiền.")
