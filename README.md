# MoneyLens AI

> **Your money, understood. Your future, predicted.**

Trợ lý tài chính cá nhân ứng dụng **AI & Machine Learning** dành cho sinh viên và người trẻ mới đi làm — tổng hợp giao dịch phân mảnh qua file CSV chuẩn 5 cột, lưu trữ bền vững bằng **SQLite**, tự động phân loại giao dịch bằng **Scikit-learn (92.6% 5-Fold CV Accuracy)**, phát hiện bất thường/định kỳ/rò rỉ chi nhỏ, dự báo dòng tiền 30 ngày bằng **Statsmodels** kèm **What-If Simulator**, và hỏi đáp trực tiếp bằng **Google Gemini 2.5 Flash LLM**.

---

## Kiến trúc hệ thống đầy đủ (Members 1 + 2 + 3)

```text
MoneyLens-AI/
├── app.py                        # [Member 1] Entry point, Navigation 4 trang, Sidebar, CSV Upload & Gemini Key
├── .streamlit/config.toml        # [Member 1] UI/UX Pro Max Swiss FinTech Theme
├── .agents/skills/ui-ux-pro-max/ # [Skill] UI UX Pro Max design intelligence skill
├── design-system/moneylens-ai/   # [Skill] Persisted Master Design System (MASTER.md)
├── pages/                        # [Member 1] 4 Màn hình MVP (Streamlit + Plotly)
│   ├── overview.py               # 01 · Tổng quan tài chính
│   ├── spending.py               # 02 · Phân tích chi tiêu + Đánh giá ML
│   ├── forecast.py               # 03 · Dự báo dòng tiền + What-If Simulator
│   └── advisor.py                # 04 · Trợ lý AI Advisor (Gemini + Charts)
├── ui/                           # [Member 1] Design System CSS, Vector SVG Icons & Adapter
│   ├── icons.py
│   ├── theme.py
│   ├── components.py
│   ├── service_adapter.py
│   └── sample_data.py
├── data/
│   ├── sample_transactions.csv   # [Member 2] Bộ dữ liệu mẫu 4 tháng (123 giao dịch VND chuẩn 5 cột)
│   └── moneylens.db              # [Member 3] SQLite tự động tạo khi chạy (không commit lên Git)
├── src/                          # [Member 2 & 3] Lõi xử lý dữ liệu, ML, Forecast & LLM
│   ├── data_processing.py        # [Member 3] Làm sạch 5 cột + SQLite Persistence
│   ├── categorization.py         # [Member 2] Scikit-learn TF-IDF + Logistic Regression (92.6% CV)
│   ├── analysis.py               # [Member 2] Spikes, IQR/Z-score Anomalies, Recurring, Micro-Spending
│   ├── forecasting.py            # [Member 2] Statsmodels Exponential Smoothing + What-If + MAE
│   └── ai_advisor.py             # [Member 3] Gemini 2.5 Flash API (Data-Grounded) + Offline Fallback
├── docs/                         # PRD, Figma Spec, Pitch Deck, Demo Script, QA, ML & Deploy Docs
├── .env.example
├── requirements.txt
└── README.md
```

---

## Quy ước dữ liệu CSV chuẩn (5 cột — VND)

| Tên cột | Kiểu dữ liệu | Ví dụ | Quy ước |
|---|---|---|---|
| `date` | Date (`YYYY-MM-DD`) | `2026-11-01` | Ngày phát sinh giao dịch |
| `description` | String | `Highlands Coffee` | Mô tả giao dịch / cửa hàng |
| `amount` | Number | `45000` | Luôn là **số dương** (VND) |
| `type` | String | `expense` | Chỉ nhận `income` hoặc `expense` |
| `category` | String | `Food` | Có thể **để trống** để Scikit-learn ML tự phân loại (`Food`, `Shopping`, `Transport`, `Bills`, `Entertainment`, `Other`) |

---

## Hướng dẫn chạy cục bộ (Quick Start)

```bash
# 1. Cài đặt toàn bộ thư viện
pip install -r requirements.txt

# 2. (Tùy chọn) Bật Gemini 2.5 Flash LLM thật
cp .env.example .env
# Mở file .env và dán GEMINI_API_KEY của bạn (hoặc dán trực tiếp ở Sidebar)

# 3. Chạy ứng dụng Streamlit
streamlit run app.py
```

---

## Tài liệu sản phẩm & Thiết kế
- **Thiết kế Figma thật (Design System + 4 Màn Hình):** https://www.figma.com/design/dYLwJMbLYDNNFDNq5riM4A
- **Master Design System (UI/UX Pro Max):** [MASTER.md](design-system/moneylens-ai/MASTER.md)
- **Nghiên cứu Pain Point & User Journey:** [01_product_research_user_journey.md](docs/01_product_research_user_journey.md)
- **Pitch Deck 10 Slides & Q&A:** [03_pitch_deck_slides.md](docs/03_pitch_deck_slides.md)
- **Kịch bản Demo 3–5 phút:** [04_demo_script.md](docs/04_demo_script.md)
- **Báo cáo Kiểm thử UX:** [05_ux_test_plan_and_report.md](docs/05_ux_test_plan_and_report.md)
- **Báo cáo AI/ML & Độ chính xác (Member 2):** [07_ai_ml_evaluation_report.md](docs/07_ai_ml_evaluation_report.md)
- **Hướng dẫn Backend, LLM & Deploy (Member 3):** [08_backend_deployment_guide.md](docs/08_backend_deployment_guide.md)
