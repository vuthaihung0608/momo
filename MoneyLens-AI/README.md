# 💸 MoneyLens-AI

> **Trợ lý Phân tích và Dự báo Tài chính Cá nhân Thông minh bằng AI dành cho Sinh viên và Người mới đi làm tại Việt Nam.**

MoneyLens-AI giúp biến những dòng sao kê giao dịch ngân hàng khô khan thành bức tranh tài chính trực quan, tự động phân loại giao dịch, phát hiện chi tiêu bất thường/định kỳ, dự báo dòng tiền 30 ngày và tư vấn tài chính thông minh qua Gemini API.

---

## 🏛️ 1. Kiến Trúc Dự Án & Nguyên Tắc Thiết Kế

Dự án áp dụng nguyên tắc **phân tách tuyệt đối giữa Logic nghiệp vụ và Giao diện người dùng (UI)**:
- Thư mục `src/`: Chứa mã nguồn Python thuần, độc lập hoàn toàn với framework UI (**tuyệt đối không import Streamlit**). Mỗi hàm đều có đầy đủ Type Hints, Docstring và khối test độc lập `if __name__ == "__main__":`.
- File `app.py` và thư mục `pages/`: Chỉ phụ trách hiển thị giao diện Streamlit, đọc dữ liệu từ `st.session_state` và gọi các hàm nghiệp vụ từ `src/`.

```
MoneyLens-AI/
├── app.py                     # [Member 1] Giao diện chính, nạp file CSV & xem trước dữ liệu
├── pages/
│   ├── overview.py            # [Member 1] Bức tranh tổng quan (KPIs + Biểu đồ dòng tiền)
│   ├── spending.py            # [Member 1] Phân tích chi tiêu, phát hiện bất thường & định kỳ
│   ├── forecast.py            # [Member 1] Dự báo số dư tương lai & cảnh báo ngân sách
│   └── advisor.py             # [Member 1] Khung chat tương tác với AI Advisor (Gemini)
├── data/
│   └── sample_transactions.csv# Bộ dữ liệu mẫu 48 dòng giao dịch thực tế
├── src/
│   ├── __init__.py            # Export toàn bộ Interface Contract
│   ├── data_processing.py     # [Member 3] Đọc, làm sạch, validate CSV giao dịch
│   ├── categorization.py      # [Member 2] Phân loại danh mục & phát hiện chi tiêu định kỳ
│   ├── analysis.py            # [Member 2] Thống kê dòng tiền, tỷ trọng chi tiêu & bất thường
│   ├── forecasting.py         # [Member 2] Thuật toán dự báo số dư & đánh giá rủi ro
│   └── ai_advisor.py          # [Member 3] Context builder & kết nối Gemini API (hỗ trợ Mock offline)
├── test_pipeline.py           # Bộ kiểm thử tích hợp toàn bộ pipeline từ đầu đến cuối
├── requirements.txt           # Danh sách thư viện phụ thuộc
├── .env.example               # Mẫu biến môi trường cấu hình API Key
├── .gitignore                 # Bỏ qua file môi trường, cache, DB
└── README.md                  # Tài liệu hướng dẫn sử dụng & phân công công việc
```

---

## 👥 2. Phân Công Trách Nhiệm & Chiến Lược Nhánh Git (Nhóm 3 người)

Để đảm bảo nhóm 3 người có thể lập trình song song mà không bị xung đột mã nguồn (merge conflict), các file đã được phân định rõ Interface Contract:

| Thành viên | Vai trò chính | Các file phụ trách | Nhánh Git đề xuất |
| :--- | :--- | :--- | :--- |
| **Member 1** | **Frontend & Streamlit UI** | `app.py`, `pages/overview.py`, `pages/spending.py`, `pages/forecast.py`, `pages/advisor.py` | `feature/ui-dashboard` |
| **Member 2** | **ML, Phân Loại & Dự Báo** | `src/categorization.py`, `src/analysis.py`, `src/forecasting.py` | `feature/ml-analytics-forecasting` |
| **Member 3** | **Data Engineering & AI Advisor** | `src/data_processing.py`, `src/ai_advisor.py`, `test_pipeline.py` | `feature/data-pipeline-gemini` |

### Quy trình làm việc với Git:
1. Tạo nhánh riêng từ `main`:
   ```bash
   git checkout -b feature/<tên-tính-năng>
   ```
2. Cài đặt các TODO được đánh dấu sẵn trong file của mình (ví dụ: `# TODO (Member 2): ...` hoặc `# TODO (Member 3): ...`).
3. Chạy kiểm thử độc lập file đang code:
   ```bash
   python -m src.<tên_file>
   ```
4. Kiểm tra toàn bộ luồng tích hợp trước khi tạo Pull Request:
   ```bash
   python test_pipeline.py
   ```

---

## 📋 3. Quy Ước Dữ Liệu CSV (Data Contract)

Mọi file CSV nạp vào hệ thống bắt buộc phải chứa đúng 5 cột sau:

| Tên Cột | Kiểu Dữ Liệu | Giá Trị Hợp Lệ | Mô Tả & Ví Dụ |
| :--- | :--- | :--- | :--- |
| `date` | String / Date | `YYYY-MM-DD` | Ngày giao dịch (ví dụ: `2026-11-01`) |
| `description` | String | Văn bản mô tả | Nội dung giao dịch (ví dụ: `Highlands Coffee`, `Tiền phòng trọ`) |
| `amount` | Float / Int | Số dương (> 0) | Số tiền giao dịch tính bằng VND (ví dụ: `45000`, `2500000`) |
| `type` | String | `income` hoặc `expense` | Phân loại dòng tiền: thu nhập (`income`) hoặc chi tiêu (`expense`) |
| `category` | String | Danh mục chi tiêu | Tên nhóm chi tiêu (ví dụ: `Food`, `Housing`, `Transport`...). *Có thể để trống để hệ thống tự động phân loại*. |

---

## 🚀 4. Hướng Dẫn Cài Đặt & Sử Dụng

### Bước 1: Sao chép cấu hình biến môi trường
Tạo file `.env` từ file mẫu `.env.example`:
```bash
cp .env.example .env
```
Mở file `.env` và điền Gemini API Key của bạn (nếu có):
```env
GEMINI_API_KEY=AIzaSy...your_actual_gemini_api_key...
```
*(Lưu ý: Nếu chưa có API Key, hệ thống vẫn hoạt động bình thường ở chế độ AI Advisor Offline Baseline).*

### Bước 2: Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 3: Chạy bộ kiểm thử tích hợp (Pipeline Tests)
```bash
python test_pipeline.py
```
Hoặc kiểm tra độc lập từng module trong `src/`:
```bash
python -m src.data_processing
python -m src.categorization
python -m src.analysis
python -m src.forecasting
python -m src.ai_advisor
```

### Bước 4: Khởi chạy ứng dụng Streamlit
```bash
streamlit run app.py
```
Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ mặc định: `http://localhost:8501`.
- Tại màn hình chính, bạn có thể tải file CSV của mình hoặc bấm **"Nạp Dữ Liệu Mẫu"** để trải nghiệm ngay.
- Sử dụng menu thanh bên trái để chuyển qua các trang **Tổng Quan**, **Chi Tiêu**, **Dự Báo** và **Trợ Lý AI**.

---

## 🛠️ 5. Lộ Trình Nâng Cấp Kỹ Thuật (Roadmap)

- **Member 2 (ML & Analytics):**
  - Thay thế rule-based keyword bằng mô hình NLP Scikit-learn (TF-IDF + LogisticRegression) huấn luyện trên tập dữ liệu tiếng Việt.
  - Nâng cấp dự báo chuỗi thời gian sang Statsmodels SARIMAX / Holt-Winters hoặc Prophet với khoảng tin cậy 95%.
  - Tích hợp IsolationForest phát hiện gian lận và chi tiêu dị biệt.
- **Member 3 (Data & AI):**
  - Tích hợp OCR quét hóa đơn / sao kê PDF ngân hàng.
  - Bổ sung bộ nhớ hội thoại ngữ cảnh dài (Conversation Memory) và Function Calling cho Gemini AI Advisor.
- **Member 1 (Frontend):**
  - Bổ sung chế độ Dark Mode, biểu đồ phân tích nhiệt (Heatmap) chi tiêu theo ngày trong tuần, và xuất báo cáo PDF tài chính hàng tháng.
