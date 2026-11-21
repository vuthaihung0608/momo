"""test_pipeline.py - Comprehensive End-to-End Test Suite for MoneyLens-AI.

Tests all 5 core modules in `src/` sequentially:
1. data_processing: Ingestion, schema validation, type cleaning
2. categorization: Auto-fill missing categories, recurring expense detection
3. analysis: Overview metrics, cashflow over time, spending breakdown, anomaly detection
4. forecasting: Balance projection, moving average burn rate, over-budget evaluation
5. ai_advisor: Context formatting and advisor query generation (baseline/mock & API)
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing import REQUIRED_COLUMNS, load_and_clean_data
from src.categorization import categorize_transactions, detect_recurring_transactions
from src.analysis import (
    get_overview_metrics,
    get_cashflow_over_time,
    get_spending_by_category,
    detect_anomalies,
)
from src.forecasting import forecast_balance
from src.ai_advisor import build_financial_context, ask_advisor


def test_data_processing() -> pd.DataFrame:
    print("[1/5] Testing src.data_processing...")
    csv_file = PROJECT_ROOT / "data" / "sample_transactions.csv"
    assert csv_file.exists(), f"Sample data not found at {csv_file}"

    df = load_and_clean_data(csv_file)

    # 1. Check returned type
    assert isinstance(df, pd.DataFrame), "load_and_clean_data must return a DataFrame"
    assert not df.empty, "DataFrame should not be empty"

    # 2. Check required columns
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Missing required column '{col}'"

    # 3. Check types
    assert pd.api.types.is_datetime64_any_dtype(df["date"]), "date column must be datetime"
    assert pd.api.types.is_numeric_dtype(df["amount"]), "amount column must be numeric"
    assert (df["amount"] > 0).all(), "All amounts must be positive"
    assert df["type"].isin(["income", "expense"]).all(), "type must only be 'income' or 'expense'"

    print(f"  -> PASS: Loaded and cleaned {len(df)} transactions successfully.")
    return df


def test_categorization(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[2/5] Testing src.categorization...")
    # Check that initial data had some blank categories
    initial_blanks = (df["category"] == "").sum()
    print(f"  -> Detected {initial_blanks} blank categories before auto-categorization.")

    categorized_df = categorize_transactions(df)
    assert isinstance(categorized_df, pd.DataFrame), "categorize_transactions must return DataFrame"
    assert len(categorized_df) == len(df), "Row count must remain identical"

    # Verify no blank categories remain
    remaining_blanks = (categorized_df["category"] == "").sum()
    assert remaining_blanks == 0, f"Expected 0 blank categories, got {remaining_blanks}"

    # Verify recurring transaction detection
    recurring_df = detect_recurring_transactions(categorized_df)
    assert isinstance(recurring_df, pd.DataFrame), "detect_recurring_transactions must return DataFrame"
    expected_recurring_cols = ["description", "amount", "count", "total_amount", "frequency"]
    for col in expected_recurring_cols:
        assert col in recurring_df.columns, f"Missing column '{col}' in recurring_df"

    print(f"  -> PASS: Auto-categorized all rows. Detected {len(recurring_df)} recurring patterns.")
    return categorized_df


def test_analysis(df: pd.DataFrame) -> dict:
    print("\n[3/5] Testing src.analysis...")

    # 1. Overview metrics
    metrics = get_overview_metrics(df)
    assert isinstance(metrics, dict), "get_overview_metrics must return a dict"
    for key in ["total_income", "total_expense", "current_balance"]:
        assert key in metrics, f"Missing required key '{key}' in metrics"
        assert isinstance(metrics[key], (int, float)), f"Metric '{key}' must be numeric"

    # Mathematical consistency check
    expected_balance = round(metrics["total_income"] - metrics["total_expense"], 2)
    assert metrics["current_balance"] == expected_balance, (
        f"Balance mismatch: {metrics['current_balance']} != {expected_balance}"
    )
    print(f"  -> Overview Metrics: Income={metrics['total_income']:,.0f}, "
          f"Expense={metrics['total_expense']:,.0f}, Balance={metrics['current_balance']:,.0f}")

    # 2. Cashflow over time
    cashflow_df = get_cashflow_over_time(df)
    assert isinstance(cashflow_df, pd.DataFrame), "get_cashflow_over_time must return DataFrame"
    cashflow_cols = ["date", "income", "expense", "net_cashflow", "cumulative_balance"]
    for col in cashflow_cols:
        assert col in cashflow_df.columns, f"Missing '{col}' in cashflow_df"
    print(f"  -> Cashflow aggregated over {len(cashflow_df)} distinct transaction dates.")

    # 3. Spending by category
    spending_df = get_spending_by_category(df)
    assert isinstance(spending_df, pd.DataFrame), "get_spending_by_category must return DataFrame"
    for col in ["category", "amount", "percentage"]:
        assert col in spending_df.columns, f"Missing '{col}' in spending_df"
    if not spending_df.empty:
        total_pct = spending_df["percentage"].sum()
        assert 99.0 <= total_pct <= 101.0, f"Percentage sum should be ~100%, got {total_pct}"
    print(f"  -> Spending breakdown computed across {len(spending_df)} categories.")

    # 4. Anomaly detection
    anomalies_df = detect_anomalies(df)
    assert isinstance(anomalies_df, pd.DataFrame), "detect_anomalies must return DataFrame"
    for col in ["date", "description", "amount", "category", "deviation_score"]:
        assert col in anomalies_df.columns, f"Missing '{col}' in anomalies_df"
    print(f"  -> Detected {len(anomalies_df)} anomalous spending transactions.")

    print("  -> PASS: src.analysis passed all contract tests.")
    return metrics


def test_forecasting(df: pd.DataFrame) -> dict:
    print("\n[4/5] Testing src.forecasting...")
    forecast = forecast_balance(df, days_ahead=30, monthly_budget=7000000.0)

    assert isinstance(forecast, dict), "forecast_balance must return a dict"
    for key in ["projected_balance", "expected_expense", "over_budget_risk", "forecast_df"]:
        assert key in forecast, f"Missing key '{key}' in forecast dictionary"

    assert isinstance(forecast["projected_balance"], (int, float))
    assert isinstance(forecast["expected_expense"], (int, float))
    assert isinstance(forecast["over_budget_risk"], bool)
    assert isinstance(forecast["forecast_df"], pd.DataFrame)
    assert len(forecast["forecast_df"]) == 30, "Forecast DataFrame should contain 30 days"

    for col in ["date", "projected_balance", "projected_daily_expense"]:
        assert col in forecast["forecast_df"].columns, f"Missing '{col}' in forecast_df"

    print(f"  -> 30-Day Forecast: Projected Balance={forecast['projected_balance']:,.0f}, "
          f"Expected Expense={forecast['expected_expense']:,.0f}, OverBudget={forecast['over_budget_risk']}")
    print("  -> PASS: src.forecasting passed all contract tests.")
    return forecast


def test_ai_advisor(df: pd.DataFrame, metrics: dict, forecast: dict):
    print("\n[5/5] Testing src.ai_advisor...")
    # 1. Test context builder
    context = build_financial_context(df, metrics, forecast)
    assert isinstance(context, str), "Context must be a string"
    assert len(context) > 50, "Context string too short"
    assert "Tổng thu nhập" in context, "Context must include income summary"

    # 2. Test advisor query (offline/mock or API)
    question = "Làm sao để sinh viên tiết kiệm được 2 triệu mỗi tháng?"
    answer = ask_advisor(question, df, metrics, forecast)
    assert isinstance(answer, str), "ask_advisor must return a string"
    assert len(answer) > 50, "Answer from advisor should not be empty"

    print("  -> AI Advisor returned valid response.")
    print("  -> PASS: src.ai_advisor passed all contract tests.")


def main():
    print("=" * 65)
    print("  MONEYLENS-AI: INTEGRATION PIPELINE VERIFICATION SUITE")
    print("=" * 65)

    df_clean = test_data_processing()
    df_categorized = test_categorization(df_clean)
    metrics = test_analysis(df_categorized)
    forecast = test_forecasting(df_categorized)
    test_ai_advisor(df_categorized, metrics, forecast)

    print("\n" + "=" * 65)
    print("  ALL 5 MODULE CONTRACTS & PIPELINES VERIFIED SUCCESSFULLY! [PASS]")
    print("=" * 65)


if __name__ == "__main__":
    main()
