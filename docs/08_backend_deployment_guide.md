# 08. Hướng dẫn Backend, Tích hợp LLM & Triển khai (Member 3 — Engineering Owner)

> **Phụ trách:** Member 3 — Backend & Integration (`Engineering Owner`)  
> **Phạm vi:** `src/data_processing.py` (CSV + SQLite), `src/ai_advisor.py` (Gemini 2.5 Flash LLM + Grounded Engine), kết nối toàn hệ thống với Frontend `ui/service_adapter.py`, và hướng dẫn Deploy lên Streamlit Community Cloud.

---

## 1. Kiến trúc Backend & Luồng dữ liệu

```text
CSV Upload / data/sample_transactions.csv
   │
   ▼
src/data_processing.py  ──► Làm sạch 5 cột (VND dương) ──► Lưu bền vững SQLite (data/moneylens.db)
   │
   ▼
src/categorization.py   ──► Scikit-learn TF-IDF + Logistic Regression tự điền các dòng trống category
   │
   ├──► src/analysis.py      (6 danh mục, MoM spikes, IQR/Z-score anomalies, định kỳ, chi nhỏ <=100k)
   ├──► src/forecasting.py   (Statsmodels Exponential Smoothing 30 ngày + What-If Simulator + MAE)
   └──► src/ai_advisor.py    (Trích xuất JSON số liệu thật ──► Gemini 2.5 Flash API / Offline Engine + Plotly chart)
```

---

## 2. Cơ sở dữ liệu SQLite (`data/moneylens.db`)

- Khởi tạo tự động bởi `init_db()` ngay lần đầu ứng dụng chạy.
- Gồm 2 bảng:
  - `transactions`: Lưu toàn bộ giao dịch đã làm sạch kèm cờ `is_auto_categorized` và `category_confidence`.
  - `app_settings`: Lưu metadata nguồn file mới nhất (`last_source_name`).
- Đã thêm `*.db` vào `.gitignore` để không đẩy file database cục bộ lên GitHub.

---

## 3. Tích hợp Google Gemini API (`src/ai_advisor.py`)

### Chống bịa số (Anti-Hallucination Grounding)
Thay vì gửi toàn bộ bảng CSV thô vào LLM (dễ sai phép cộng), `src/ai_advisor.py` tính toán chính xác bằng Pandas/NumPy trước:
- Tổng thu, tổng chi, số dư ròng, số dư tích lũy, tỷ lệ tiết kiệm.
- Top 6 danh mục chi tiêu + % tăng/giảm so với tháng trước.
- Danh sách giao dịch bất thường, chi phí định kỳ, khoản chi nhỏ lặp lại.
- Dự báo dòng tiền 30 ngày + phép tính tự động cho kịch bản mua lớn (VD: *"mua laptop 15 triệu"*).

Sau đó khối sự thật đã xác minh này mới được nạp vào `gemini-2.5-flash` (qua SDK `google-genai`) với `temperature=0.3`.

### Cách kích hoạt Gemini API Key (2 cách)
1. **Chạy cục bộ (`.env`):** Copy `.env.example` thành `.env` rồi điền `GEMINI_API_KEY=AIza...`.
2. **Trực tiếp trên giao diện:** Mở mục **Cấu hình Gemini LLM API** ở thanh Sidebar và dán API Key (không lưu xuống disk).
3. **Chế độ dự phòng (Zero-Cost Offline Fallback):** Nếu không nhập API Key hoặc phòng thi mất mạng, hệ thống tự chuyển mượt sang **MoneyLens Grounded Engine** và vẫn trả lời kèm biểu đồ Plotly bình thường.

---

## 4. Hướng dẫn Deploy lên Streamlit Community Cloud (Miễn phí cho Demo cuộc thi)

1. Push toàn bộ thư mục `MoneyLens-AI/` lên repository GitHub (nhánh `main`).
2. Truy cập https://share.streamlit.io và đăng nhập bằng GitHub.
3. Chọn **New app** → chọn repo `MoneyLens-AI`, branch `main`, Main file path: `app.py`.
4. (Tùy chọn) Mở **Advanced settings → Secrets** và thêm:
   ```toml
   GEMINI_API_KEY = "AIza..."
   ```
5. Nhấn **Deploy!** — sau ~2 phút sẽ có link HTTPS công khai gửi cho Ban Giám Khảo & chèn QR Code vào Slide 10.
