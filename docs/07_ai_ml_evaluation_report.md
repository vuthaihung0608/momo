# 07. Báo cáo Thiết kế Dữ liệu, Mô hình AI/ML & Đánh giá Độ chính xác (Member 2 — AI Owner)

> **Phụ trách:** Member 2 — Data & AI (`AI Owner`)  
> **Các module đã hoàn thiện:** `data/sample_transactions.csv`, `src/categorization.py`, `src/analysis.py`, `src/forecasting.py`.

---

## 1. Thiết kế bộ dữ liệu giao dịch (`data/sample_transactions.csv`)

- **Quy chuẩn:** Đúng **5 cột** (`date, description, amount, type, category`), `type ∈ {income, expense}`, `amount > 0`, đơn vị **VND**.
- **Quy mô:** **123 giao dịch** trải dài **4 tháng** (`2026-08` đến `2026-11`) phản ánh chân thực hành vi sinh viên / người trẻ mới đi làm tại Việt Nam (Shopee, TikTok Shop, MoMo, GrabFood, ShopeeFood, Highlands, Phúc Long, GrabBike, Xanh SM, Tiền trọ, EVN, FPT, Viettel 4G, Spotify, Netflix, iCloud+, CGV, Fahasa, Long Châu).
- **Cố tình để trống `category` ở 14 giao dịch** (tháng 10 & tháng 11) để chứng minh trực quan khả năng tự phân loại tự động của mô hình ML ngay trên giao diện demo.

---

## 2. Mô hình Phân loại Giao dịch (`src/categorization.py`)

### Kiến trúc lựa chọn
Tuân thủ nguyên tắc kỹ thuật tinh gọn (không lạm dụng Deep Learning nặng nề cho bài toán văn bản ngắn tiếng Việt):
- **Trích xuất đặc trưng (`FeatureUnion`):** Kết hợp `TfidfVectorizer(ngram_range=(1, 2))` (từ/cụm từ) + `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))` (ký tự — chịu lỗi viết tắt/không dấu tiếng Việt rất tốt như `tra sua`, `dien nuoc`, `grabbike`).
- **Bộ phân loại chính:** `LogisticRegression(C=4.0, max_iter=1000)` trên tập huấn luyện cân bằng **216 mẫu giao dịch Việt–Anh** (36 mẫu/danh mục × 6 danh mục chi tiêu).
- **Lớp Hybrid Disambiguation:** Bổ sung luật chính xác cao để phân biệt các tiền tố thương hiệu dễ nhầm (VD: `GrabFood` → `Food` vs `GrabBike` → `Transport`; `ShopeeFood` → `Food` vs `Shopee` → `Shopping`).

### Kết quả Đánh giá Độ chính xác (5-Fold Stratified Cross-Validation)

| Mô hình (Scikit-learn) | Accuracy (5-Fold CV) | Macro F1-Score | Nhận xét |
|---|---|---|---|
| **TF-IDF (Word+Char) + Logistic Regression (Đang dùng)** | **92.6%** | **92.6%** | Nhanh (< 20ms), tuyến tính tối ưu cho dữ liệu văn bản ngắn có chiều cao |
| TF-IDF (Word+Char) + Random Forest (Đối chứng) | 82.4% | 82.5% | Kém hơn ~10.2% trên không gian đặc trưng thưa (sparse TF-IDF) |

#### Chi tiết Precision / Recall / F1 theo từng danh mục (Logistic Regression — 5-Fold CV)

| Danh mục | Precision (%) | Recall (%) | F1-Score (%) | Số mẫu kiểm thử |
|---|---|---|---|---|
| **Shopping (Mua sắm)** | 100.0% | 97.2% | 98.6% | 36 |
| **Bills (Hóa đơn)** | 92.1% | 97.2% | 94.6% | 36 |
| **Entertainment (Giải trí)** | 94.4% | 94.4% | 94.4% | 36 |
| **Food (Ăn uống)** | 97.0% | 88.9% | 92.8% | 36 |
| **Transport (Di chuyển)** | 87.2% | 94.4% | 90.7% | 36 |
| **Other (Khác)** | 85.7% | 83.3% | 84.5% | 36 |

---

## 3. Phân tích Hành vi, Bất thường & Rò rỉ Chi tiêu (`src/analysis.py`)

1. **Phát hiện tăng đột biến (MoM Spike):** Cảnh báo tự động khi danh mục tăng `>= +20%` và chênh lệch `>= 200.000 ₫` (phát hiện chính xác **Mua sắm +281%** dịp 11.11 và **Ăn uống +27%**).
2. **Phát hiện giao dịch bất thường (Anomaly Detection):** Kết hợp ngưỡng **IQR upper fence (`Q3 + 1.8×IQR`)** và **Z-score (`mean + 2σ`)** theo từng danh mục (loại trừ hóa đơn cố định định kỳ). Bắt trúng `Shopee 11.11 - Tai nghe Sony chống ồn (2.650.000 ₫)` và `MoMo thanh toán lẩu băng chuyền (460.000 ₫)`.
3. **Rule-based Recurring & Subscription Detection:** Quét các khoản lặp lại qua `>= 60%` số tháng lịch sử với hệ số biến thiên số tiền `CV <= 0.22` → phát hiện chuẩn xác **7 khoản định kỳ/subscriptions** (Phòng trọ, Điện nước, Internet FPT, 4G Viettel, Netflix, Spotify, iCloud+).
4. **Phát hiện Rò rỉ Khoản chi nhỏ (`Micro-Spending <= 100.000 ₫`):** Gom nhóm các khoản nhỏ (cà phê, trà sữa, ăn vặt, GrabBike) giải quyết trực tiếp pain point *"Khó phát hiện những khoản chi nhỏ nhưng lặp lại"*.

---

## 4. Mô hình Dự báo Dòng tiền (`src/forecasting.py`)

- **Phương pháp:** **Statsmodels Simple Exponential Smoothing (`SimpleExpSmoothing`)** kết hợp Winsorization (giảm nhiễu từ giao dịch đột biến đơn lẻ như mua tai nghe 2.65tr) trên chuỗi chi tiêu biến đổi hàng ngày, tự động rơi về **Moving Average Baseline** khi lịch sử < 14 ngày.
- **Lịch hóa đơn & thu nhập:** Cộng/trừ chính xác các hóa đơn định kỳ theo ngày dự kiến và chu kỳ thu nhập hàng tháng.
- **Kiểm định Backtest trên dữ liệu 4 tháng (`113 ngày`):**
  - Mô hình active: **Statsmodels Exponential Smoothing (SES)**
  - **MAE hàng ngày:** ~`106.210 ₫/ngày`
  - **Hỗ trợ What-If Simulator:** Tính tức thời tác động của cắt giảm % theo danh mục, hủy subscriptions, hoặc khoản mua lớn (VD: Laptop 15 triệu).
