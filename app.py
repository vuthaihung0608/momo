"""MoneyLens AI — Production Web Application.

Features:
- Google Sign-In (Live OAuth 2.0 when configured + instant per-account Google Sign-In locally)
- Mandatory First-Time Personal Onboarding (Full Name, Occupation, Income, Budget, Goal — zero hardcoded persona!)
- 100% Legal Real-Time Auto-Updating Bank Sync (Embedded Webhook Receiver for SePay, Casso, PayOS & SMS/Email/App Forwarding)
- Quick Offline Capture ("Xăng 100k"), Bill Photo OCR Vision, Scikit-learn ML (92.6% CV), Statsmodels 30-day Forecast, AI Advisor
- Dual Light/Dark Theme, Bilingual VI/EN & Floating Circular AI Help Widget

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import timedelta

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pages import advisor as page_advisor
from pages import forecast as page_forecast
from pages import overview as page_overview
from pages import spending as page_spending
from ui.components import render_floating_help_chat
from ui.i18n import cat_label
from ui.layout import (
    render_google_signin_screen,
    render_left_workspace_panel,
    render_onboarding_screen,
    render_sub_navigation,
    render_top_header,
)
from ui.service_adapter import (
    create_user_session,
    ensure_email_watcher_running,
    ensure_webhook_server_running,
    exchange_google_oauth_code,
    get_app_setting,
    get_available_months,
    get_transactions_since_id,
    get_user_by_id,
    get_user_by_session_token,
    get_user_sync_signature,
    load_transactions_from_db,
    sign_in_with_google_profile,
)
from ui.theme import format_vnd, inject_global_css

st.set_page_config(
    page_title="MoneyLens AI · Personal Finance Intelligence",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _init_state() -> None:
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "light"
    if "lang" not in st.session_state:
        st.session_state["lang"] = "vi"
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "overview"
    if "gemini_api_key" not in st.session_state:
        st.session_state["gemini_api_key"] = os.getenv("GEMINI_API_KEY", "") or get_app_setting("ai_api_key", "")
    if "auto_sync_enabled" not in st.session_state:
        st.session_state["auto_sync_enabled"] = True
    if "force_reload_db" not in st.session_state:
        st.session_state["force_reload_db"] = True
    if "current_user" not in st.session_state:
        sid = st.query_params.get("sid")
        sid_str = sid[0] if isinstance(sid, list) else str(sid or "")
        restored = get_user_by_session_token(sid_str) if sid_str else None
        st.session_state["current_user"] = restored
        if restored is not None:
            st.session_state["monthly_budget"] = int(restored["monthly_budget"])


def _handle_google_oauth_callback() -> None:
    """Complete live Google OAuth 2.0 redirect if `?code=...` is present in query params."""
    code = st.query_params.get("code")
    if not code:
        return
    code_str = code[0] if isinstance(code, list) else str(code)
    st.query_params.clear()
    profile, err = exchange_google_oauth_code(code_str)
    if err or profile is None:
        st.session_state["oauth_error_msg"] = err or "Google OAuth failed."
        return
    user, u_err = sign_in_with_google_profile(
        email=profile["email"],
        full_name=profile.get("full_name", ""),
        avatar_url=profile.get("avatar_url", ""),
        google_sub=profile.get("google_sub", ""),
    )
    if u_err or user is None:
        st.session_state["oauth_error_msg"] = u_err or "Could not create user."
        return
    st.session_state["current_user"] = user
    st.session_state["monthly_budget"] = int(user["monthly_budget"])
    st.session_state["force_reload_db"] = True
    st.session_state["selected_month"] = None
    st.session_state.pop("db_sync_sig", None)
    st.query_params["sid"] = create_user_session(user["id"])


@st.fragment(run_every=timedelta(seconds=4))
def _live_bank_sync_watcher(user_id: int, lang: str) -> None:
    """Lightweight 4-second SQLite poller — auto-refreshes the entire dashboard when a Webhook arrives!"""
    if not st.session_state.get("auto_sync_enabled", True):
        return
    cur_sig = get_user_sync_signature(user_id)
    prev_sig = st.session_state.get("db_sync_sig")
    if prev_sig is None:
        st.session_state["db_sync_sig"] = cur_sig
        return
    if cur_sig != prev_sig:
        prev_max_id = int(prev_sig[1])
        new_rows = get_transactions_since_id(user_id, prev_max_id)
        st.session_state["db_sync_sig"] = cur_sig
        st.session_state["force_reload_db"] = True
        if new_rows:
            latest = new_rows[-1]
            sgn = "+" if latest["type"] == "income" else "-"
            msg = (
                f"Tự động đồng bộ {len(new_rows)} giao dịch mới: **{latest['description']}** "
                f"({sgn}{format_vnd(latest['amount'])} → {cat_label(latest['category'], lang)})"
                if lang == "vi"
                else f"Auto-synced {len(new_rows)} new transaction(s): **{latest['description']}** "
                f"({sgn}{format_vnd(latest['amount'])} → {cat_label(latest['category'], lang)})"
            )
            st.session_state["incoming_sync_toast"] = msg
        st.rerun(scope="app")


# Boot embedded legal Webhook HTTP receiver & Email Bank Auto-Sync watcher once per process
webhook_ok, _webhook_port = ensure_webhook_server_running()
ensure_email_watcher_running()

_init_state()
_handle_google_oauth_callback()

theme_mode: str = st.session_state["theme_mode"]
lang: str = st.session_state["lang"]

# Inject dynamic Light/Dark CSS (with high-contrast Dark Mode placeholders & white topbar icons!)
inject_global_css(theme_mode)

# Refresh active user record from SQLite if logged in
user: dict | None = st.session_state.get("current_user")
if user is not None:
    fresh_user = get_user_by_id(user["id"])
    if fresh_user is not None:
        user = fresh_user
        st.session_state["current_user"] = user

# 1. Row 1: Top Deep Navy Global Header Bar (Dynamic per-user profile chip — never hardcoded!)
render_top_header(user=user, theme_mode=theme_mode, lang=lang)

if st.session_state.get("oauth_error_msg"):
    st.error(st.session_state.pop("oauth_error_msg"))

# ---------------------------------------------------------------------------
# STATE A: Signed Out → Google Sign-In Gate
# ---------------------------------------------------------------------------
if user is None:
    render_google_signin_screen(theme_mode=theme_mode, lang=lang)
    render_floating_help_chat(lang=lang, api_key=str(st.session_state.get("gemini_api_key", "")))
    st.stop()

# ---------------------------------------------------------------------------
# STATE B: First-Time Sign-In → Mandatory Personal Onboarding Form
# ---------------------------------------------------------------------------
if not user.get("onboarding_completed", False):
    render_onboarding_screen(user=user, theme_mode=theme_mode, lang=lang)
    render_floating_help_chat(lang=lang, api_key=str(st.session_state.get("gemini_api_key", "")))
    st.stop()

# ---------------------------------------------------------------------------
# STATE C: Authenticated & Onboarded → Full Personalized MoneyLens AI Workspace
# ---------------------------------------------------------------------------
if st.session_state.get("incoming_sync_toast"):
    st.toast(st.session_state.pop("incoming_sync_toast"), icon=":material/sync:")

if "monthly_budget" not in st.session_state:
    st.session_state["monthly_budget"] = int(user["monthly_budget"])

if "chat_messages" not in st.session_state:
    disp_name = user["full_name"] or user["email"]
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                f"Xin chào **{disp_name}**! Mình là **MoneyLens AI** — trợ lý tài chính cá nhân dựa trực tiếp trên dữ liệu giao dịch thực tế của bạn.\n\n"
                "Bạn có thể bấm câu hỏi gợi ý bên trên hoặc hỏi tự nhiên, ví dụ:\n"
                "- *\"Tôi tiêu nhiều nhất vào đâu?\"*\n"
                "- *\"Nếu tháng sau tôi mua laptop 15 triệu thì sao?\"*"
                if lang == "vi"
                else f"Hello **{disp_name}**! I'm **MoneyLens AI** — your personal finance advisor grounded in your own live data."
            ),
            "chart": None,
            "source": "MoneyLens AI",
        }
    ]

# Load active user's transactions from SQLite & keep sync signature current
if st.session_state.get("force_reload_db", True) or "transactions_df" not in st.session_state:
    st.session_state["transactions_df"] = load_transactions_from_db(user_id=user["id"])
    st.session_state["db_sync_sig"] = get_user_sync_signature(user["id"])
    st.session_state["force_reload_db"] = False

df = st.session_state["transactions_df"]
avail_months = get_available_months(df)
if not st.session_state.get("selected_month") or (
    st.session_state["selected_month"] != "ALL" and st.session_state["selected_month"] not in avail_months
):
    st.session_state["selected_month"] = avail_months[0] if avail_months else "ALL"

selected_month: str = st.session_state["selected_month"]
monthly_budget: int = int(st.session_state.get("monthly_budget", user["monthly_budget"]))
active_page: str = st.session_state["active_page"]
has_gemini = bool(str(st.session_state.get("gemini_api_key", "")).strip())

# 2. Row 2: Horizontal Sub-Navigation Bar
render_sub_navigation(
    active_page=active_page,
    total_tx=len(df),
    selected_month=selected_month,
    has_gemini=has_gemini,
    webhook_ok=webhook_ok,
    theme_mode=theme_mode,
    lang=lang,
)

# 3. Row 3: 2-Column Workspace Layout (Left AI Capture & Real-Time Auto-Sync | Right Main Dashboard)
left_col, main_col = st.columns([0.28, 0.72], gap="large")

with left_col:
    render_left_workspace_panel(
        user=user,
        df=df,
        avail_months=avail_months,
        selected_month=selected_month,
        monthly_budget=monthly_budget,
        theme_mode=theme_mode,
        lang=lang,
    )

with main_col:
    if active_page == "overview":
        page_overview.render(df, selected_month, float(monthly_budget), theme_mode=theme_mode, lang=lang, user=user)
    elif active_page == "spending":
        page_spending.render(df, selected_month, float(monthly_budget), theme_mode=theme_mode, lang=lang, user=user)
    elif active_page == "forecast":
        page_forecast.render(df, selected_month, float(monthly_budget), theme_mode=theme_mode, lang=lang, user=user)
    elif active_page == "advisor":
        page_advisor.render(df, selected_month, float(monthly_budget), theme_mode=theme_mode, lang=lang, user=user)

# 4. Background 4-Second Live Bank Auto-Sync Fragment (Zero flicker when idle; auto-updates app when webhook hits!)
_live_bank_sync_watcher(user["id"], lang)

# 5. Bottom-Right Floating Circular AI Help Widget
render_floating_help_chat(lang=lang, api_key=str(st.session_state.get("gemini_api_key", "")))
