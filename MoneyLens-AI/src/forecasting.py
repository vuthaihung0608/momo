"""Module: forecasting.py
Owner: Member 2

Provides financial trajectory forecasting and future balance estimation
using baseline moving averages and risk threshold evaluation.
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def forecast_balance(
    df: pd.DataFrame,
    days_ahead: int = 30,
    monthly_budget: float | None = None,
) -> dict[str, Any]:
    """Forecast future cash balance and evaluate over-budget risk over a given horizon.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions DataFrame with columns ['date', 'amount', 'type'].
    days_ahead : int, optional
        Number of calendar days to forecast into the future, by default 30.
    monthly_budget : float | None, optional
        User-defined monthly spending budget cap in VND. If None, risk is evaluated
        against running out of cash (balance < 0).

    Returns
    -------
    dict[str, Any]
        Dictionary containing forecast results:
        - 'projected_balance': float, estimated ending balance after `days_ahead` days.
        - 'expected_expense': float, estimated total spending over `days_ahead` days.
        - 'over_budget_risk': bool, True if projected spending exceeds budget or balance < 0.
        - 'forecast_df': pd.DataFrame, future daily projection curve with columns:
          ['date', 'projected_balance', 'projected_daily_expense'].
    """
    if df.empty:
        empty_forecast = pd.DataFrame(
            columns=["date", "projected_balance", "projected_daily_expense"]
        )
        return {
            "projected_balance": 0.0,
            "expected_expense": 0.0,
            "over_budget_risk": False,
            "forecast_df": empty_forecast,
        }

    # 1. Calculate current financial state
    total_income = float(df[df["type"] == "income"]["amount"].sum())
    total_expense = float(df[df["type"] == "expense"]["amount"].sum())
    current_balance = total_income - total_expense

    # 2. Estimate daily expense burn rate
    expense_df = df[df["type"] == "expense"].copy()
    if expense_df.empty:
        daily_expense_rate = 0.0
    else:
        min_date = pd.to_datetime(df["date"]).min()
        max_date = pd.to_datetime(df["date"]).max()
        days_span = max((max_date - min_date).days + 1, 1)

        # Baseline: Moving average of daily spending
        daily_expense_rate = float(total_expense / days_span)

    # 3. Forecast future trajectory
    expected_expense = float(daily_expense_rate * days_ahead)
    projected_balance = float(current_balance - expected_expense)

    # 4. Assess budget & overdraft risk
    if monthly_budget is not None and monthly_budget > 0:
        # Scale budget proportionally if days_ahead != 30
        effective_budget = (monthly_budget / 30.0) * days_ahead
        over_budget_risk = bool(expected_expense > effective_budget or projected_balance < 0)
    else:
        over_budget_risk = bool(projected_balance < 0)

    # 5. Build forecast DataFrame
    start_forecast_date = pd.to_datetime(df["date"]).max() + pd.Timedelta(days=1)
    future_dates = pd.date_range(start=start_forecast_date, periods=days_ahead, freq="D")

    # Linear daily decline based on daily burn rate
    projected_balances = [
        current_balance - (daily_expense_rate * (i + 1))
        for i in range(days_ahead)
    ]

    forecast_df = pd.DataFrame({
        "date": future_dates,
        "projected_balance": [round(b, 2) for b in projected_balances],
        "projected_daily_expense": [round(daily_expense_rate, 2)] * days_ahead,
    })

    # TODO (Member 2): Nâng cấp thuật toán dự báo từ Moving Average đơn giản
    # lên mô hình chuỗi thời gian Statsmodels (ARIMA/SARIMAX), Holt-Winters
    # hoặc Prophet để nhận diện yếu tố mùa vụ (đầu tháng lĩnh lương, cuối tháng kẹt tiền)
    # và xuất khoảng tin cậy 95% (Confidence Intervals: upper_bound, lower_bound).

    return {
        "projected_balance": round(projected_balance, 2),
        "expected_expense": round(expected_expense, 2),
        "over_budget_risk": over_budget_risk,
        "forecast_df": forecast_df,
    }


if __name__ == "__main__":
    print("=== Testing src.forecasting ===")
    mock_df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-11-01", "2026-11-02", "2026-11-05", "2026-11-10", "2026-11-15"
        ]),
        "description": ["Lương", "Tiền trọ", "Ăn uống", "Đi lại", "Mua sắm"],
        "amount": [8000000.0, 2500000.0, 500000.0, 300000.0, 700000.0],
        "type": ["income", "expense", "expense", "expense", "expense"],
        "category": ["Salary", "Housing", "Food", "Transport", "Shopping"],
    })

    res = forecast_balance(mock_df, days_ahead=30, monthly_budget=5000000.0)
    print("Forecast Result Summary:")
    print(f"- Projected Balance: {res['projected_balance']:,.2f} VND")
    print(f"- Expected Expense:  {res['expected_expense']:,.2f} VND")
    print(f"- Over Budget Risk:  {res['over_budget_risk']}")
    print("\nForecast Curve Preview (First 5 days):")
    print(res["forecast_df"].head())

    assert "projected_balance" in res
    assert "expected_expense" in res
    assert "over_budget_risk" in res
    assert "forecast_df" in res
    assert len(res["forecast_df"]) == 30
    print("\n[PASS] src.forecasting self-test completed successfully!")
