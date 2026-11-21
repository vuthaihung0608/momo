"""Trang Dự báo Tài chính (Forecast).
Ước tính số dư tương lai, kiểm soát ngân sách chi tiêu và cảnh báo rủi ro thâm hụt.
"""

from __future__ import annotations

import sys
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st

# Setup sys.path to import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing import load_and_clean_data
from src.categorization import categorize_transactions
from src.analysis import get_overview_metrics
from src.forecasting import forecast_balance

st.set_page_config(page_title="Dự Báo Tài Chính | MoneyLens-AI", page_icon="🔮", layout="wide")


def ensure_data():
    """Ensure session state contains cleaned data, fallback to sample CSV."""
    if "df" not in st.session_state or st.session_state["df"] is None or st.session_state["df"].empty:
        sample_path = PROJECT_ROOT / "data" / "sample_transactions.csv"
        raw_df = load_and_clean_data(sample_path)
        st.session_state["df"] = categorize_transactions(raw_df)
        st.session_state["data_source"] = "Tự động nạp mẫu (sample_transactions.csv)"


ensure_data()
df = st.session_state["df"]

st.title("🔮 Dự Báo Số Dư & Kiểm Soát Ngân Sách")
st.caption(f"Dữ liệu đang dùng: {st.session_state.get('data_source', 'Không rõ')}")

metrics = get_overview_metrics(df)

# Forecast Controls
st.subheader("⚙️ Thiết Lập Tham Số Dự Báo")
col_input1, col_input2 = st.columns([1, 1], gap="medium")

with col_input1:
    budget_input = st.number_input(
        "Hạn mức ngân sách chi tiêu tháng mong muốn (VND):",
        min_value=0.0,
        value=5000000.0,
        step=500000.0,
        format="%.0f",
        help="Ngân sách chi tiêu tối đa bạn mong muốn duy trì trong 1 tháng (30 ngày).",
    )

with col_input2:
    days_input = st.slider(
        "Khoảng thời gian dự báo tương lai (ngày):",
        min_value=7,
        max_value=90,
        value=30,
        step=1,
        help="Số ngày muốn dự báo xu hướng số dư tiếp theo.",
    )

# Run Forecast
forecast_res = forecast_balance(df, days_ahead=days_input, monthly_budget=budget_input)

st.divider()

# Forecast KPI Cards
st.subheader(f"📊 Kết Quả Dự Báo Cho {days_input} Ngày Tới")

c1, c2, c3 = st.columns(3)
c1.metric(
    label="💎 Số Dư Hiện Tại",
    value=f"{metrics['current_balance']:,.0f} VND",
)
c2.metric(
    label=f"📉 Dự Kiến Chi Tiêu ({days_input} ngày)",
    value=f"{forecast_res['expected_expense']:,.0f} VND",
    delta=f"Hạn mức: {budget_input:,.0f} VND",
    delta_color="off",
)
c3.metric(
    label=f"🔮 Số Dư Ước Tính Sau {days_input} Ngày",
    value=f"{forecast_res['projected_balance']:,.0f} VND",
    delta=f"{forecast_res['projected_balance'] - metrics['current_balance']:,.0f} VND",
    delta_color="normal",
)

# Over-budget warning banner
if forecast_res["over_budget_risk"]:
    st.error(
        f"⚠️ **CẢNH BÁO RỦI RO:** Dựa trên tốc độ chi tiêu bình quân hiện tại, tổng chi dự kiến "
        f"(**{forecast_res['expected_expense']:,.0f} VND**) sẽ vượt ngân sách mục tiêu hoặc khiến số dư bị âm! "
        f"Hãy chủ động cắt giảm các khoản chi không thiết yếu."
    )
else:
    st.success(
        f"✅ **AN TOÀN:** Chi tiêu dự kiến nằm trong ngân sách cho phép. "
        f"Bạn có khả năng duy trì số dư dương **{forecast_res['projected_balance']:,.0f} VND** sau {days_input} ngày."
    )

# Forecast Trajectory Chart
st.divider()
st.subheader("📉 Biểu Đồ Đường Xu Hướng Số Dư Tương Lai")

forecast_df = forecast_res["forecast_df"]

if not forecast_df.empty:
    fig_f = go.Figure()

    # Projected balance line
    fig_f.add_trace(
        go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["projected_balance"],
            name="Số Dư Dự Báo",
            mode="lines+markers",
            line=dict(color="#f59e0b", width=3, dash="dash"),
        )
    )

    # Zero baseline warning line
    fig_f.add_hline(
        y=0,
        line_dash="dot",
        line_color="red",
        annotation_text="Ngưỡng thâm hụt (0 VND)",
        annotation_position="bottom right",
    )

    fig_f.update_layout(
        title=f"Mô Phỏng Xu Hướng Số Dư Trong {days_input} Ngày Tới (Moving Average Baseline)",
        xaxis_title="Thời Gian Dự Báo",
        yaxis_title="Số Dư Ước Tính (VND)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        height=420,
    )

    st.plotly_chart(fig_f, use_container_width=True)

    with st.expander("📋 Xem chi tiết bảng dự báo từng ngày"):
        st.dataframe(
            forecast_df.style.format({
                "projected_balance": "{:,.0f} VND",
                "projected_daily_expense": "{:,.0f} VND",
                "date": lambda d: d.strftime("%Y-%m-%d"),
            }),
            use_container_width=True,
        )
