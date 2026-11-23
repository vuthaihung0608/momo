# 06. Hợp đồng Tích hợp (Integration Contract) & Quy trình Git nhóm — MoneyLens AI

> **Phụ trách:** Member 1 — Product & Frontend (`Product Owner`)  
> **Mục tiêu:** Giúp **Member 2 (Data & AI)** và **Member 3 (Backend & Integration)** ghép code `src/*.py` và `data/sample_transactions.csv` vào giao diện Streamlit của Member 1 **không xung đột Git (zero merge conflict)** và chạy mượt ngay lập tức.

---

## 1. Phân chia quyền sở hữu file trên Git (Tránh Merge Conflict)

| Thành viên | File / Thư mục sở hữu | Ghi chú |
|---|---|---|
| **Member 1 (Product & Frontend)** | `app.py`, `pages/overview.py`, `pages/spending.py`, `pages/forecast.py`, `pages/advisor.py`, `ui/*`, `.streamlit/config.toml`, `docs/*` | Không chỉnh trực tiếp vào `src/*` hoặc `data/sample_transactions.csv` để tránh xung đột với Member 2 & 3 |
| **Member 2 (Data & AI)** | `data/sample_transactions.csv`, `src/categorization.py`, `src/analysis.py`, `src/forecasting.py` | Dùng đúng chuẩn CSV 5 cột VND |
| **Member 3 (Backend & Integration)** | `src/data_processing.py`, `src/ai_advisor.py`, deploy Streamlit Cloud | Chịu trách nhiệm nối LLM API (Gemini) & kiểm tra toàn luồng |
| **Dùng chung (thống nhất khi merge)** | `requirements.txt`, `README.md`, `.gitignore` | Merge cẩn thận nếu cả hai bên cùng thêm thư viện |

---

## 2. Cơ chế Tự động Kết nối (`ui/service_adapter.py`)

Frontend của Member 1 đã có lớp cầu nối **`ui/service_adapter.py`**:
- **Hiện tại (khi `src/` chưa có code):** Frontend chạy **Standalone Mode** bằng dữ liệu mẫu sinh viên (`ui/sample_data.py`) và logic baseline bằng Pandas/NumPy để Member 1 kiểm thử UX & tập demo ngay lập tức.
- **Ngay khi Member 2 & 3 push file vào `data/` và `src/`:**
  1. Nếu tồn tại `data/sample_transactions.csv` → app tự ưu tiên tải file của Member 2!
  2. Nếu tồn tại các hàm đúng chữ ký bên dưới trong `src/*.py` → `ui/service_adapter.py` tự gọi code thật và hiển thị trạng thái **`🟢 Live AI Backend (5/5 module)`** ngay ở cuối Sidebar!

---

## 3. Chữ ký hàm chuẩn (Function Signatures) dành cho Member 2 & Member 3

### 3.1. `src/data_processing.py` (Member 3)
```python
def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: DataFrame gồm đúng 5 cột ['date', 'description', 'amount', 'type', 'category']
    Output: DataFrame đã làm sạch ngày, chuẩn hóa type ('income'/'expense'), amount > 0 (VND).
    """
```

### 3.2. `src/categorization.py` (Member 2)
```python
def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: DataFrame đã làm sạch, có thể có dòng 'category' bị rỗng ('').
    Output: DataFrame đã điền đầy đủ 'category' vào 6 nhóm chi tiêu chuẩn:
            ['Food', 'Shopping', 'Transport', 'Bills', 'Entertainment', 'Other']
            và 'Income' cho dòng type == 'income'.
    """
```

### 3.3. `src/analysis.py` (Member 2 — tùy chọn ghi đè)
```python
def analyze_spending(df: pd.DataFrame, selected_month: str) -> dict:
    """
    Output dict tối thiểu gồm:
      - total_expense: float
      - top_category: str
      - top_category_amount: float
      - top_category_share: float
      - category_breakdown: DataFrame[category, amount, tx_count, share_pct, prev_amount, change_pct]
      - spikes: list[dict]
      - monthly_category_trend: DataFrame[year_month, category, amount]
      - recurring: DataFrame[merchant, category, avg_amount, months_count, typical_day, annual_cost, next_due_date]
      - anomalies: DataFrame[date, description, category, amount, cat_avg, ratio, reason]
      - recurring_monthly_total: float
    """
```

### 3.4. `src/forecasting.py` (Member 2 — tùy chọn ghi đè)
```python
def forecast_cashflow(df: pd.DataFrame, monthly_budget: float, scenario: dict) -> dict:
    """
    scenario keys: cut_food_pct, cut_shopping_pct, cut_entertainment_pct,
                   extra_one_time_expense, cancel_subscriptions
    Output dict gồm 'timeline' (DataFrame[date, segment, base_balance, scenario_balance, upper_band, lower_band])
    và các chỉ số KPI cuối tháng / rủi ro vượt ngân sách.
    """
```

### 3.5. `src/ai_advisor.py` (Member 3 — Gemini LLM API)
```python
def ask_advisor(question: str, df: pd.DataFrame, context: dict) -> dict | str:
    """
    Input:
      - question: Câu hỏi tiếng Việt của người dùng
      - df: DataFrame giao dịch hiện tại
      - context: dict chứa selected_month, monthly_budget, overview, spending_top_category,
                 recurring_total, forecast_eom_balance
    Output:
      - Chuỗi Markdown câu trả lời, HOẶC
      - dict {"answer": str, "chart": plotly.graph_objects.Figure | None, "source": "Gemini AI Advisor"}
    """
```

---

## 4. Quy trình đẩy code lên Git chung (Khi bạn trong nhóm gửi link Repo)

Khi nhận được link repo (VD: `https://github.com/<org>/MoneyLens-AI.git`), Member 1 chỉ cần chạy các bước sau (hoặc gửi link cho trợ lý thao tác giúp):

```bash
# 1. Khởi tạo git hoặc clone repo chung rồi copy phần của Member 1 vào
git init
git remote add origin <LINK_REPO_GIT_CHUNG>

# 2. Lấy trạng thái mới nhất từ nhóm (nếu repo đã có commit)
git fetch origin
git checkout -b feature/member1-frontend

# 3. Kiểm tra danh sách file thuộc Member 1 (không đụng src/ & data/)
git status

# 4. Commit & Push lên nhánh riêng của Member 1 để tạo Pull Request gọn gàng
git add app.py pages/ ui/ .streamlit/ docs/ requirements.txt .gitignore README.md
git commit -m "feat(frontend): complete Member 1 Streamlit dashboard, UX docs, Figma spec & demo script"
git push -u origin feature/member1-frontend
```

> **Mẹo:** Dùng nhánh riêng `feature/member1-frontend` rồi mở **Pull Request** vào `main` giúp cả nhóm review sạch sẽ và không bao giờ ghi đè nhầm code của Member 2 & Member 3!
