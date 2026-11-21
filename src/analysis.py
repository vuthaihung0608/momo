"""Module: analysis.py
Owner: Member 2

Provides core financial analytics, cashflow aggregations,
spending breakdowns by category, and statistical anomaly detection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def get_overview_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Calculate key financial summary metrics from transaction history.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with columns ['amount', 'type'].

    Returns
    -------
    dict[str, float]
        Dictionary with exactly 3 keys:
        - 'total_income': Total income amount (float)
        - 'total_expense': Total expense amount (float)
        - 'current_balance': Net balance = total_income - total_expense (float)
    """
    if df.empty:
        return {
            "total_income": 0.0,
            "total_expense": 0.0,
            "current_balance": 0.0,
        }

    income_mask = df["type"] == "income"
    expense_mask = df["type"] == "expense"

    total_income = float(df.loc[income_mask, "amount"].sum())
    total_expense = float(df.loc[expense_mask, "amount"].sum())
    current_balance = float(total_income - total_expense)

    # TODO (Member 2): Bổ sung thêm các chỉ số tài chính nâng cao:
    # savings_rate = current_balance / total_income, burn_rate_per_day,
    # và tỷ lệ tăng trưởng so với tháng trước (MoM Growth).

    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "current_balance": round(current_balance, 2),
    }


def get_cashflow_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily income, expense, net cashflow, and running cumulative balance.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with columns ['date', 'amount', 'type'].

    Returns
    -------
    pd.DataFrame
        DataFrame sorted by date containing columns:
        ['date', 'income', 'expense', 'net_cashflow', 'cumulative_balance'].
    """
    columns = ["date", "income", "expense", "net_cashflow", "cumulative_balance"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df = df.copy()
    # Normalize date to date-only without time component
    df["date_only"] = pd.to_datetime(df["date"]).dt.date

    # Pivot income and expense by date
    daily_income = (
        df[df["type"] == "income"]
        .groupby("date_only")["amount"]
        .sum()
        .rename("income")
    )
    daily_expense = (
        df[df["type"] == "expense"]
        .groupby("date_only")["amount"]
        .sum()
        .rename("expense")
    )

    all_dates = sorted(df["date_only"].unique())
    cashflow = pd.DataFrame({"date_only": all_dates})
    cashflow = cashflow.merge(daily_income, on="date_only", how="left").fillna({"income": 0.0})
    cashflow = cashflow.merge(daily_expense, on="date_only", how="left").fillna({"expense": 0.0})

    cashflow["net_cashflow"] = cashflow["income"] - cashflow["expense"]
    cashflow["cumulative_balance"] = cashflow["net_cashflow"].cumsum()
    cashflow = cashflow.rename(columns={"date_only": "date"})
    cashflow["date"] = pd.to_datetime(cashflow["date"])

    # TODO (Member 2): Hỗ trợ gom nhóm linh hoạt theo Tuần (W) hoặc Tháng (M),
    # và tính toán độ biến động dòng tiền (Cashflow Volatility Index).

    return cashflow[columns]


def get_spending_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate expense distribution and percentage by category.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with columns ['category', 'amount', 'type'].

    Returns
    -------
    pd.DataFrame
        DataFrame sorted by 'amount' descending with columns:
        ['category', 'amount', 'percentage'].
    """
    columns = ["category", "amount", "percentage"]
    expense_df = df[df["type"] == "expense"]

    if expense_df.empty:
        return pd.DataFrame(columns=columns)

    grouped = (
        expense_df.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values(by="amount", ascending=False)
    )

    total_expense = grouped["amount"].sum()
    if total_expense > 0:
        grouped["percentage"] = (grouped["amount"] / total_expense * 100).round(2)
    else:
        grouped["percentage"] = 0.0

    grouped["amount"] = grouped["amount"].round(2)

    # TODO (Member 2): Tích hợp so sánh với ngân sách định mức (Budget Allocation)
    # và vẽ biểu đồ Pareto 80/20 danh mục chi tiêu chính.

    return grouped[columns].reset_index(drop=True)


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Detect anomalous expense transactions exceeding statistical threshold (mean + 2 * std).

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with columns ['date', 'description', 'amount', 'type', 'category'].

    Returns
    -------
    pd.DataFrame
        DataFrame of anomalous expense records with columns:
        ['date', 'description', 'amount', 'category', 'deviation_score'].
    """
    columns = ["date", "description", "amount", "category", "deviation_score"]
    expense_df = df[df["type"] == "expense"].copy()

    if len(expense_df) < 3:
        return pd.DataFrame(columns=columns)

    mean_val = float(expense_df["amount"].mean())
    std_val = float(expense_df["amount"].std(ddof=1))

    if std_val == 0.0 or np.isnan(std_val):
        threshold = mean_val * 2.0
        anomalies = expense_df[expense_df["amount"] > threshold].copy()
        anomalies["deviation_score"] = 2.0
    else:
        threshold = mean_val + 2.0 * std_val
        anomalies = expense_df[expense_df["amount"] > threshold].copy()
        anomalies["deviation_score"] = (
            (anomalies["amount"] - mean_val) / std_val
        ).round(2)

    anomalies = anomalies.sort_values(by="amount", ascending=False).reset_index(drop=True)

    # TODO (Member 2): Nâng cấp phát hiện bất thường bằng Scikit-learn
    # (IsolationForest hoặc LocalOutlierFactor) theo từng phân nhóm chi tiêu riêng biệt.

    return anomalies[columns]


if __name__ == "__main__":
    print("=== Testing src.analysis ===")
    mock_df = pd.DataFrame({
        "date": pd.to_datetime(["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04"]),
        "description": ["Lương", "Tiền trọ", "Cà phê", "Mua laptop đột xuất"],
        "amount": [10000000.0, 2500000.0, 50000.0, 6000000.0],
        "type": ["income", "expense", "expense", "expense"],
        "category": ["Salary", "Housing", "Food", "Shopping"],
    })

    metrics = get_overview_metrics(mock_df)
    print("Overview Metrics:", metrics)
    assert metrics["total_income"] == 10000000.0
    assert metrics["total_expense"] == 8550000.0
    assert metrics["current_balance"] == 1450000.0

    cashflow = get_cashflow_over_time(mock_df)
    print("\nCashflow Table:")
    print(cashflow)
    assert "cumulative_balance" in cashflow.columns

    spending = get_spending_by_category(mock_df)
    print("\nSpending by Category:")
    print(spending)
    assert not spending.empty

    anomalies = detect_anomalies(mock_df)
    print("\nAnomalies:")
    print(anomalies)
    print("\n[PASS] src.analysis self-test completed successfully!")
