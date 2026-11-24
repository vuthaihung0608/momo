"""Unified Service Adapter connecting Frontend to Multi-User SQLite, Google Auth, Live Webhooks, ML, Forecasting & LLM."""

from __future__ import annotations

import importlib
from typing import Any

import pandas as pd

from src.ai_advisor import ask_advisor as _backend_ask_advisor
from src.analysis import analyze_spending as _backend_analyze_spending
from src.analysis import get_previous_month
from src.auth import (
    authenticate_user,
    complete_user_onboarding,
    create_user_session,
    delete_user_session,
    exchange_google_oauth_code,
    get_google_oauth_url,
    get_user_by_id,
    get_user_by_session_token,
    is_google_oauth_configured,
    list_google_accounts,
    regenerate_webhook_token,
    register_user,
    sign_in_with_google_profile,
    update_user_budget,
    update_user_profile,
)
from src.categorization import categorize_transactions as _backend_categorize
from src.categorization import evaluate_categorization_model as _backend_eval_ml
from src.data_processing import (
    clean_transactions as _backend_clean,
    delete_fixed_expense,
    delete_transaction,
    delete_transactions_bulk,
    get_app_setting,
    get_db_summary,
    get_email_sync_config,
    get_recent_webhook_events,
    get_transactions_since_id,
    get_user_sync_signature,
    insert_fixed_expense,
    insert_transaction,
    load_fixed_expenses,
    load_transactions_from_db,
    parse_csv_source,
    save_transactions_to_db,
    seed_user_demo_transactions,
    set_app_setting,
)
from src.email_bank_sync import (
    ensure_email_watcher_running,
    import_selected_bank_transactions,
    preview_user_bank_emails,
    save_and_test_email_config,
    scan_user_bank_emails_now,
    simulate_bank_email_preview,
    simulate_bank_email_scan,
)
from src.forecasting import forecast_cashflow as _backend_forecast
from src.webhook_server import (
    ensure_webhook_server_running,
    get_webhook_base_url,
    get_webhook_port,
    is_webhook_server_healthy,
    send_live_test_webhook,
)


def _has_callable(module_name: str, func_name: str) -> bool:
    try:
        mod = importlib.import_module(module_name)
        return callable(getattr(mod, func_name, None))
    except Exception:
        return False


def get_backend_status() -> dict[str, bool]:
    """Inspect connected backend modules in `src/`."""
    return {
        "data_processing": _has_callable("src.data_processing", "clean_transactions"),
        "categorization": _has_callable("src.categorization", "categorize_transactions"),
        "analysis": _has_callable("src.analysis", "analyze_spending"),
        "forecasting": _has_callable("src.forecasting", "forecast_cashflow"),
        "ai_advisor": _has_callable("src.ai_advisor", "ask_advisor"),
        "webhook_server": _has_callable("src.webhook_server", "ensure_webhook_server_running"),
    }


def get_available_months(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return []
    return sorted(df["year_month"].dropna().unique().tolist(), reverse=True)


def filter_by_month(df: pd.DataFrame, month: str) -> pd.DataFrame:
    if df is None or df.empty or month == "ALL":
        return df.copy()
    return df.loc[df["year_month"] == month].copy()


def compute_overview_metrics(df: pd.DataFrame, selected_month: str) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "income": 0.0, "expense": 0.0, "net_balance": 0.0, "cumulative_balance": 0.0,
            "savings_rate": 0.0, "prev_month": None, "income_delta_pct": None,
            "expense_delta_pct": None, "tx_count": 0, "auto_cat_count": 0,
        }
    cur_df = filter_by_month(df, selected_month)
    income = float(cur_df.loc[cur_df["type"] == "income", "amount"].sum())
    expense = float(cur_df.loc[cur_df["type"] == "expense", "amount"].sum())
    net_balance = income - expense
    savings_rate = (net_balance / income * 100.0) if income > 0 else 0.0

    up_to = df if selected_month == "ALL" else df.loc[df["year_month"] <= selected_month]
    cumulative_balance = float(up_to["signed_amount"].sum())

    prev_month = get_previous_month(df, selected_month) if selected_month != "ALL" else None
    income_delta_pct = None
    expense_delta_pct = None
    if prev_month:
        prev_df = filter_by_month(df, prev_month)
        prev_inc = float(prev_df.loc[prev_df["type"] == "income", "amount"].sum())
        prev_exp = float(prev_df.loc[prev_df["type"] == "expense", "amount"].sum())
        if prev_inc > 0:
            income_delta_pct = (income - prev_inc) / prev_inc * 100.0
        if prev_exp > 0:
            expense_delta_pct = (expense - prev_exp) / prev_exp * 100.0

    return {
        "income": income,
        "expense": expense,
        "net_balance": net_balance,
        "cumulative_balance": cumulative_balance,
        "savings_rate": savings_rate,
        "prev_month": prev_month,
        "income_delta_pct": income_delta_pct,
        "expense_delta_pct": expense_delta_pct,
        "tx_count": int(len(cur_df)),
        "auto_cat_count": int(cur_df["is_auto_categorized"].sum()),
    }


def analyze_spending(
    df: pd.DataFrame,
    selected_month: str,
    fixed_expenses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _backend_analyze_spending(df, selected_month, fixed_expenses=fixed_expenses)


def get_ml_evaluation() -> dict[str, Any]:
    return _backend_eval_ml()


def forecast_cashflow(
    df: pd.DataFrame,
    monthly_budget: float = 8_000_000,
    cut_food_pct: int = 0,
    cut_shopping_pct: int = 0,
    cut_entertainment_pct: int = 0,
    extra_one_time_expense: float = 0.0,
    extra_expense_label: str = "Khoản mua sắm dự kiến",
    cancel_subscriptions: bool = False,
    fixed_expenses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _backend_forecast(
        df=df,
        monthly_budget=monthly_budget,
        scenario={
            "cut_food_pct": cut_food_pct,
            "cut_shopping_pct": cut_shopping_pct,
            "cut_entertainment_pct": cut_entertainment_pct,
            "extra_one_time_expense": extra_one_time_expense,
            "extra_expense_label": extra_expense_label,
            "cancel_subscriptions": cancel_subscriptions,
        },
        fixed_expenses=fixed_expenses,
    )


def ask_advisor(
    question: str,
    df: pd.DataFrame,
    selected_month: str,
    monthly_budget: float,
    api_key: str = "",
    history: list[dict[str, Any]] | None = None,
    lang: str = "vi",
    fixed_expenses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _backend_ask_advisor(
        question=question,
        df=df,
        context={
            "selected_month": selected_month,
            "monthly_budget": monthly_budget,
            "api_key": api_key,
            "history": history,
            "lang": lang,
            "fixed_expenses": fixed_expenses,
        },
    )


__all__ = [
    "analyze_spending",
    "ask_advisor",
    "authenticate_user",
    "complete_user_onboarding",
    "compute_overview_metrics",
    "create_user_session",
    "delete_fixed_expense",
    "delete_transaction",
    "delete_transactions_bulk",
    "delete_user_session",
    "ensure_email_watcher_running",
    "ensure_webhook_server_running",
    "exchange_google_oauth_code",
    "filter_by_month",
    "forecast_cashflow",
    "get_app_setting",
    "get_available_months",
    "get_backend_status",
    "get_db_summary",
    "get_email_sync_config",
    "get_google_oauth_url",
    "get_ml_evaluation",
    "get_recent_webhook_events",
    "get_transactions_since_id",
    "get_user_by_id",
    "get_user_by_session_token",
    "get_user_sync_signature",
    "get_webhook_base_url",
    "get_webhook_port",
    "import_selected_bank_transactions",
    "insert_fixed_expense",
    "insert_transaction",
    "is_google_oauth_configured",
    "is_webhook_server_healthy",
    "list_google_accounts",
    "load_fixed_expenses",
    "load_transactions_from_db",
    "preview_user_bank_emails",
    "regenerate_webhook_token",
    "register_user",
    "save_and_test_email_config",
    "scan_user_bank_emails_now",
    "seed_user_demo_transactions",
    "send_live_test_webhook",
    "set_app_setting",
    "sign_in_with_google_profile",
    "simulate_bank_email_preview",
    "simulate_bank_email_scan",
    "update_user_budget",
    "update_user_profile",
]
