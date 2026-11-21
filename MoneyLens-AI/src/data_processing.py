"""Module: data_processing.py
Owner: Member 3

Provides robust CSV ingestion, schema validation, data cleaning,
and type normalization for financial transactions.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: list[str] = ["date", "description", "amount", "type", "category"]


def load_and_clean_data(file_path_or_buffer: str | Path | io.StringIO | io.BytesIO | Any) -> pd.DataFrame:
    """Load transaction data from a CSV path or file buffer, validate columns, and clean fields.

    Parameters
    ----------
    file_path_or_buffer : str | Path | io.StringIO | io.BytesIO | Any
        File path string, Path object, or file-like buffer (e.g. from Streamlit file_uploader).

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame containing columns:
        ['date', 'description', 'amount', 'type', 'category'].
        - 'date': datetime64
        - 'description': stripped str
        - 'amount': positive float
        - 'type': str ('income' or 'expense')
        - 'category': str or empty string

    Raises
    ------
    ValueError
        If required columns are missing, or if no valid rows remain after cleaning.
    """
    # 1. Read CSV source
    try:
        df = pd.read_csv(file_path_or_buffer)
    except Exception as exc:
        raise ValueError(f"Không thể đọc file CSV: {exc}") from exc

    # 2. Validate required columns contract
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"File CSV thiếu các cột bắt buộc: {missing_cols}. "
            f"Cần đảm bảo đủ 5 cột: {REQUIRED_COLUMNS}"
        )

    # Work on a copy with only the required columns
    df = df[REQUIRED_COLUMNS].copy()

    # Drop entirely blank rows
    df = df.dropna(how="all")

    # 3. Clean and parse 'date'
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # 4. Clean and parse 'amount' (must be positive float)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["amount"])
    df["amount"] = df["amount"].abs().astype(float)
    df = df[df["amount"] > 0]

    # 5. Normalize 'type' ('income' or 'expense')
    df["type"] = df["type"].astype(str).str.strip().str.lower()
    df = df[df["type"].isin(["income", "expense"])]

    # 6. Normalize 'description'
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df = df[df["description"] != ""]

    # 7. Normalize 'category' (preserve blank/NaN for auto-categorization)
    df["category"] = df["category"].fillna("").astype(str).str.strip()

    # 8. Sort chronologically and reset index
    df = df.sort_values(by="date", ascending=True).reset_index(drop=True)

    if df.empty:
        raise ValueError("Không còn dòng dữ liệu hợp lệ nào sau khi làm sạch.")

    # TODO (Member 3): Nâng cấp pipeline xác thực schema với Pydantic/Pandera,
    # hỗ trợ đọc sao kê ngân hàng nhiều định dạng (Excel, Vietcombank, Techcombank, MB Bank)
    # và tự động loại bỏ giao dịch trùng lặp (deduplication).

    return df


if __name__ == "__main__":
    import tempfile

    print("=== Testing src.data_processing ===")
    sample_csv_text = """date,description,amount,type,category
2026-11-01,Lương thực tập,5000000,income,Salary
2026-11-02,Tiền trọ,2500000,expense,Housing
2026-11-03,Highlands Coffee,-45000,expense,
2026-11-04,Invalid row,abc,expense,Other
"""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
        tmp.write(sample_csv_text)
        tmp_path = tmp.name

    result_df = load_and_clean_data(tmp_path)
    print("Cleaned DataFrame:")
    print(result_df)
    print("\nData Types:")
    print(result_df.dtypes)
    assert len(result_df) == 3, f"Expected 3 rows, got {len(result_df)}"
    assert (result_df["amount"] > 0).all(), "All amounts must be positive"
    assert pd.api.types.is_datetime64_any_dtype(result_df["date"]), "Date column must be datetime"
    print("\n[PASS] src.data_processing self-test completed successfully!")
