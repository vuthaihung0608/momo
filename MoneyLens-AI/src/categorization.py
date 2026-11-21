"""Module: categorization.py
Owner: Member 2

Provides automated transaction categorization using rule-based heuristics
and detection of recurring transactions (subscriptions, utilities, rent).
"""

from __future__ import annotations

import re
import unicodedata
import pandas as pd


def _normalize_text(text: str) -> str:
    """Normalize Vietnamese text by lowercasing and removing tone marks for fuzzy matching."""
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    without_diacritics = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return without_diacritics


# Baseline keyword dictionary for auto-categorization
KEYWORD_RULES: dict[str, list[str]] = {
    "Housing": [
        "phòng trọ", "phong tro", "tiền trọ", "tien tro", "nhà trọ", "nha tro",
        "tiền nhà", "tien nha", "thuê phòng", "thue phong", "tiền điện", "tien dien",
        "tiền nước", "tien nuoc", "điện nước", "dien nuoc", "internet", "wifi",
        "fpt", "viettel", "chung cư", "phí dịch vụ", "tro", "trọ"
    ],
    "Transport": [
        "grab", "grabbike", "grabcar", "be", "bebike", "becar", "gojek",
        "xăng", "xang", "petrol", "petrolimex", "xe bus", "xe buyt", "gửi xe",
        "gui xe", "vé xe", "ve xe", "taxi", "bảo dưỡng xe"
    ],
    "Food": [
        "coffee", "cafe", "highlands", "aha", "phở", "pho", "bún", "bun",
        "cơm", "com", "bánh mì", "banh mi", "trà sữa", "tra sua", "phúc long",
        "phuc long", "lẩu", "lau", "nướng", "nuong", "kfc", "lotteria", "pizza",
        "ăn trưa", "an trua", "ăn tối", "an toi", "ăn uống", "an uong", "quán ăn"
    ],
    "Entertainment": [
        "netflix", "spotify", "cgv", "bhd", "lotte cinema", "xem phim",
        "rạp phim", "rap phim", "game", "steam", "playstation", "youtube"
    ],
    "Salary": [
        "lương", "luong", "salary", "thù lao", "thu lao", "part-time",
        "parttime", "thưởng", "thuong", "kpi", "hoa hồng"
    ],
    "Transfer": [
        "chuyển khoản", "chuyen khoan", "ck", "trả nợ", "tra no",
        "trợ cấp", "tro cap", "momo", "zalopay", "lì xì", "li xi", "quà", "qua"
    ],
    "Shopping": [
        "shopee", "lazada", "tiki", "tiktok shop", "uniqlo", "zara",
        "quần áo", "quan ao", "giày", "giay", "mua sắm", "mua sam"
    ],
    "Education": [
        "sách", "sach", "khóa học", "khoa hoc", "udemy", "coursera",
        "học phí", "hoc phi", "fahasa", "giáo trình", "giao trinh"
    ],
}


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Auto-fill missing or empty transaction categories using rule-based keyword matching.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transactions DataFrame with columns:
        ['date', 'description', 'amount', 'type', 'category'].

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with filled 'category' column. Missing entries are
        classified into matched categories or assigned 'Other'.
    """
    df = df.copy()

    def infer_category(row: pd.Series) -> str:
        current_cat = str(row["category"]).strip()
        if current_cat and current_cat.lower() not in ["", "nan", "none"]:
            return current_cat

        desc = str(row["description"])
        desc_norm = _normalize_text(desc)
        tx_type = str(row["type"]).strip().lower()

        # Match against predefined keywords
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                kw_norm = _normalize_text(kw)
                # If keyword length >= 4, safe for substring match (e.g. 'grab', 'highlands', 'phong tro')
                # If short (< 4 chars), use word boundaries to avoid false positives (e.g. 'be', 'ck')
                if len(kw_norm) >= 4:
                    if kw_norm in desc_norm:
                        return category
                else:
                    pattern = rf"(?:\b|^){re.escape(kw_norm)}(?:\b|$)"
                    if re.search(pattern, desc_norm):
                        return category

        # Fallback category based on transaction type
        if tx_type == "income":
            return "Salary" if ("lương" in desc_norm or "luong" in desc_norm) else "Other"
        return "Other"

    df["category"] = df.apply(infer_category, axis=1)

    # TODO (Member 2): Nâng cấp mô hình phân loại tự động bằng Scikit-learn:
    # sử dụng TfidfVectorizer kết hợp LogisticRegression / LinearSVC hoặc PhoBERT
    # huấn luyện trên tập dữ liệu giao dịch ngân hàng thực tế có gán nhãn.

    return df


def detect_recurring_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Detect recurring transactions (such as rent, utilities, subscriptions) based on frequency and amount.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with at least ['description', 'amount', 'type'].

    Returns
    -------
    pd.DataFrame
        DataFrame of recurring patterns with columns:
        ['description', 'amount', 'count', 'total_amount', 'frequency'].
    """
    if df.empty:
        return pd.DataFrame(columns=["description", "amount", "count", "total_amount", "frequency"])

    # Baseline rule: Group by description and check occurrences >= 2
    expense_df = df[df["type"] == "expense"].copy()
    if expense_df.empty:
        expense_df = df.copy()

    # Normalize description for grouping
    expense_df["desc_clean"] = expense_df["description"].str.strip()

    grouped = (
        expense_df.groupby("desc_clean")
        .agg(
            count=("amount", "count"),
            avg_amount=("amount", "mean"),
            total_amount=("amount", "sum"),
        )
        .reset_index()
    )

    recurring = grouped[grouped["count"] >= 2].copy()
    recurring = recurring.rename(columns={"desc_clean": "description", "avg_amount": "amount"})
    recurring["amount"] = recurring["amount"].round(2)
    recurring["total_amount"] = recurring["total_amount"].round(2)

    # Simple heuristic for frequency label
    def assign_frequency(count: int) -> str:
        if count >= 3:
            return "Monthly / Định kỳ"
        return "Frequent / Lặp lại"

    recurring["frequency"] = recurring["count"].apply(assign_frequency)
    recurring = recurring.sort_values(by="count", ascending=False).reset_index(drop=True)

    # TODO (Member 2): Cải tiến phát hiện chu kỳ bằng time-delta interval analysis
    # (tính toán phương sai số ngày giữa các lần xuất hiện để phân biệt Weekly vs Monthly).

    return recurring[["description", "amount", "count", "total_amount", "frequency"]]


if __name__ == "__main__":
    print("=== Testing src.categorization ===")
    mock_df = pd.DataFrame({
        "date": pd.to_datetime(["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-10", "2026-11-15"]),
        "description": [
            "Highlands Coffee trà sen",
            "GrabBike đi học",
            "Tiền phòng trọ tháng 11",
            "Spotify Premium",
            "Spotify Premium",
        ],
        "amount": [59000.0, 32000.0, 2500000.0, 59000.0, 59000.0],
        "type": ["expense", "expense", "expense", "expense", "expense"],
        "category": ["", "", "", "Entertainment", ""],
    })

    categorized = categorize_transactions(mock_df)
    print("Categorized DataFrame:")
    print(categorized[["description", "category"]])
    assert categorized.loc[0, "category"] == "Food"
    assert categorized.loc[1, "category"] == "Transport"
    assert categorized.loc[2, "category"] == "Housing"
    assert categorized.loc[4, "category"] == "Entertainment"

    recurring = detect_recurring_transactions(categorized)
    print("\nRecurring Transactions:")
    print(recurring)
    assert not recurring.empty, "Spotify Premium should be detected as recurring"
    print("\n[PASS] src.categorization self-test completed successfully!")
