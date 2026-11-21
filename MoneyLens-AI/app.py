"""MoneyLens-AI: Ứng dụng Phân tích và Dự báo Tài chính Cá nhân bằng AI.
Trang chủ điều hướng và quản lý nạp dữ liệu giao dịch.
"""

from __future__ import annotations

import sys
from pathlib import Path
import streamlit as st

# Setup sys.path to import from src/
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing import load_and_clean_data
from src.categorization import categorize_transactions

# Page Configuration
st.set_page_config(
    page_title="MoneyLens-AI | Trang Chủ",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Header & Welcome Banner
st.title("💸 MoneyLens-AI")
st.markdown(
    "### Trợ lý Phân tích & Dự báo Tài chính Cá nhân Thông minh cho Sinh viên & Người mới đi làm"
)
st.write(
    "MoneyLens-AI giúp bạn biến những dòng sao kê giao dịch ngân hàng khô khan thành góc nhìn tài chính "
    "trực quan, phát hiện thói quen chi tiêu rò rỉ, dự báo số dư tương lai và nhận lời khuyên thông minh từ AI."
)

st.divider()

# Section: Data Ingestion
st.subheader("📂 1. Nạp Dữ Liệu Giao Dịch")

col1, col2 = st.columns([1, 1], gap="medium")

sample_file_path = PROJECT_ROOT / "data" / "sample_transactions.csv"

with col1:
    st.markdown("**Cách 1: Tải lên file CSV cá nhân**")
    uploaded_file = st.file_uploader(
        "Chọn file CSV giao dịch (chuẩn 5 cột: date, description, amount, type, category)",
        type=["csv"],
        help="Đảm bảo file CSV có đủ các cột date, description, amount, type, category.",
    )
    if uploaded_file is not None:
        try:
            with st.spinner("Đang làm sạch và tự động phân loại dữ liệu..."):
                raw_df = load_and_clean_data(uploaded_file)
                st.session_state["df"] = categorize_transactions(raw_df)
                st.session_state["data_source"] = f"File tải lên: {uploaded_file.name}"
            st.success(f"✅ Đã nạp thành công {len(st.session_state['df'])} giao dịch từ file của bạn!")
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file: {e}")

with col2:
    st.markdown("**Cách 2: Sử dụng dữ liệu mẫu thực tế**")
    st.write(
        "Chưa có sẵn file? Bấm nút bên dưới để trải nghiệm ngay với bộ dữ liệu mẫu gồm 48 giao dịch "
        "thực tế (lương part-time, tiền trọ, Highlands Coffee, Grab, Netflix, học tập...)."
    )
    if st.button("🚀 Nạp Dữ Liệu Mẫu (Sample Transactions)", type="primary", use_container_width=True):
        try:
            with st.spinner("Đang tải dữ liệu mẫu..."):
                raw_df = load_and_clean_data(sample_file_path)
                st.session_state["df"] = categorize_transactions(raw_df)
                st.session_state["data_source"] = "Bộ dữ liệu mẫu thực tế (sample_transactions.csv)"
            st.success(f"✅ Đã nạp thành công {len(st.session_state['df'])} giao dịch mẫu!")
        except Exception as e:
            st.error(f"❌ Không thể tải dữ liệu mẫu: {e}")

# Display current data status and preview
st.divider()
st.subheader("📋 2. Trạng Thái Dữ Liệu Hiện Tại")

if "df" in st.session_state and st.session_state["df"] is not None and not st.session_state["df"].empty:
    current_df = st.session_state["df"]
    data_src = st.session_state.get("data_source", "Không xác định")
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Nguồn dữ liệu", data_src)
    col_stat2.metric("Số lượng giao dịch", f"{len(current_df)} bản ghi")
    date_range = f"{current_df['date'].min().strftime('%d/%m/%Y')} - {current_df['date'].max().strftime('%d/%m/%Y')}"
    col_stat3.metric("Khoảng thời gian", date_range)

    with st.expander("🔍 Xem trước bảng giao dịch đã làm sạch & phân loại", expanded=False):
        st.dataframe(
            current_df.style.format({
                "amount": "{:,.0f} VND",
                "date": lambda d: d.strftime("%Y-%m-%d"),
            }),
            use_container_width=True,
            height=300,
        )
else:
    st.info("ℹ️ Hiện chưa có dữ liệu trong phiên làm việc. Vui lòng tải file CSV hoặc nhấn nút **Nạp Dữ Liệu Mẫu** ở trên.")

# Section: Screen Navigation Guide
st.divider()
st.subheader("🧭 3. Hướng Dẫn Các Màn Hình Chức Năng")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("### 📊 Tổng Quan\n**pages/overview.py**")
    st.write("Xem tổng thu nhập, tổng chi tiêu, số dư ròng và biểu đồ diễn biến dòng tiền lũy kế theo thời gian.")

with c2:
    st.markdown("### 🛒 Chi Tiêu\n**pages/spending.py**")
    st.write("Phân tích cơ cấu chi tiêu theo danh mục, phát hiện giao dịch bất thường và điểm danh các khoản phí định kỳ.")

with c3:
    st.markdown("### 🔮 Dự Báo\n**pages/forecast.py**")
    st.write("Ước tính số dư 30 ngày tới dựa trên tốc độ tiêu tiền bình quân và cảnh báo nguy cơ vượt ngân sách.")

with c4:
    st.markdown("### 🤖 Trợ Lý AI\n**pages/advisor.py**")
    st.write("Hỏi đáp trực tiếp với AI Advisor (Gemini) để nhận lời khuyên tối ưu ngân sách cá nhân phù hợp.")

st.sidebar.success("💡 Chọn trang chức năng ở menu bên trái để bắt đầu khám phá!")
