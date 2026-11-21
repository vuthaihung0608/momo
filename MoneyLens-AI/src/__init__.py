"""MoneyLens-AI - Core Financial Engine Package.

This package provides pure Python modules for data loading, transaction
categorization, financial analytics, balance forecasting, and the AI advisor.
All modules in `src/` are decoupled from any UI framework (no Streamlit imports).
"""

__all__ = [
    "REQUIRED_COLUMNS",
    "load_and_clean_data",
    "categorize_transactions",
    "detect_recurring_transactions",
    "get_overview_metrics",
    "get_cashflow_over_time",
    "get_spending_by_category",
    "detect_anomalies",
    "forecast_balance",
    "build_financial_context",
    "ask_advisor",
]


def __getattr__(name: str):
    """Lazy module attribute loader conforming to PEP 562 to avoid circular and runpy import warnings."""
    if name in ("REQUIRED_COLUMNS", "load_and_clean_data"):
        from . import data_processing
        return getattr(data_processing, name)
    if name in ("categorize_transactions", "detect_recurring_transactions"):
        from . import categorization
        return getattr(categorization, name)
    if name in ("get_overview_metrics", "get_cashflow_over_time", "get_spending_by_category", "detect_anomalies"):
        from . import analysis
        return getattr(analysis, name)
    if name == "forecast_balance":
        from . import forecasting
        return getattr(forecasting, name)
    if name in ("build_financial_context", "ask_advisor"):
        from . import ai_advisor
        return getattr(ai_advisor, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
