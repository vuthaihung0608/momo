"""Screen 4 – AI Advisor (Dual Theme, VI/EN, Gemini 2.5 Flash + Data-Grounded Inline Charts)."""

from __future__ import annotations

import html
import pandas as pd
import streamlit as st

from ui.components import render_ai_banner
from ui.i18n import fmt_month_label, t
from ui.service_adapter import ask_advisor, compute_overview_metrics, load_fixed_expenses
from ui.theme import format_vnd


def render(
    df: pd.DataFrame,
    selected_month: str,
    monthly_budget: float,
    theme_mode: str = "light",
    lang: str = "vi",
    user: dict | None = None,
) -> None:
    gemini_key = str(st.session_state.get("gemini_api_key", "")).strip()
    period_label = fmt_month_label(selected_month, lang=lang, is_latest=False)

    h1, h2 = st.columns([3.5, 1.0], vertical_alignment="center")
    with h1:
        st.markdown(
            f"""
            <h1 class="ml-page-title">{html.escape(t('adv_title', lang))}</h1>
            <div class="ml-page-subtitle">{html.escape(t('adv_sub', lang))}</div>
            """,
            unsafe_allow_html=True,
        )
    with h2:
        if st.button(t("new_chat", lang), icon=":material/refresh:", key="adv_reset_chat", width="stretch"):
            st.session_state["chat_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        "Đã làm mới hội thoại. Bạn muốn MoneyLens AI phân tích điều gì từ dữ liệu tài chính của bạn?"
                        if lang == "vi"
                        else "Chat reset! What would you like MoneyLens AI to analyze from your transactions?"
                    ),
                    "chart": None,
                    "source": "MoneyLens AI",
                }
            ]
            st.rerun()

    fixed_expenses = load_fixed_expenses(user["id"]) if user else []
    metrics = compute_overview_metrics(df, selected_month)
    render_ai_banner(
        title=f"{'Trợ lý AI toàn năng · Dữ liệu đang gắn' if lang == 'vi' else 'Universal AI Advisor · Live Context'} ({period_label})",
        body_html=(
            f"<strong>{metrics['tx_count']}</strong> {t('tx_short', lang)} · "
            f"{t('income_opt', lang)}: <strong class='ml-num'>{format_vnd(metrics['income'])}</strong> · "
            f"{t('expense_opt', lang)}: <strong class='ml-num'>{format_vnd(metrics['expense'])}</strong> · "
            f"{t('kpi_balance', lang)}: <strong class='ml-num'>{format_vnd(metrics['cumulative_balance'])}</strong> · "
            f"Budget: <strong class='ml-num'>{format_vnd(monthly_budget)}</strong>"
        ),
        icon_name="database",
        theme_mode=theme_mode,
    )

    st.markdown(f"**{t('quick_prompts_lbl', lang)}**")

    quick_prompts = (
        [
            "Tôi tiêu nhiều nhất vào đâu?",
            "Nếu tháng sau tôi mua laptop 15 triệu thì sao?",
            "Tháng này tôi có khoản chi định kỳ nào dễ quên không?",
            "Danh mục nào của tôi đang tăng bất thường?",
            "Làm sao để tôi tiết kiệm thêm 2 triệu mỗi tháng?",
            "Tóm tắt sức khỏe tài chính của tôi hiện tại",
        ]
        if lang == "vi"
        else [
            "Where do I spend the most money?",
            "What if I buy a 15 triệu laptop next month?",
            "Which recurring subscriptions might I forget?",
            "Which spending category is spiking?",
            "How can I save an extra 2 triệu per month?",
            "Summarize my current financial health",
        ]
    )

    pending_prompt: str | None = None
    row1 = st.columns(3)
    for idx, col in enumerate(row1):
        with col:
            if st.button(quick_prompts[idx], icon=":material/chat_bubble:", key=f"adv_qp_{idx}", width="stretch"):
                pending_prompt = quick_prompts[idx]

    row2 = st.columns(3)
    for idx, col in enumerate(row2, start=3):
        with col:
            if st.button(quick_prompts[idx], icon=":material/chat_bubble:", key=f"adv_qp_{idx}", width="stretch"):
                pending_prompt = quick_prompts[idx]

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state["chat_messages"]):
        av = ":material/auto_awesome:" if msg["role"] == "assistant" else ":material/person:"
        with st.chat_message(msg["role"], avatar=av):
            st.markdown(msg["content"])
            if msg.get("chart") is not None:
                st.plotly_chart(msg["chart"], key=f"advisor_chart_{i}", config={"displayModeBar": False})
            if msg["role"] == "assistant" and msg.get("source"):
                st.caption(f"{'Nguồn phân tích' if lang == 'vi' else 'Source'}: {msg['source']}")

    user_typed = st.chat_input(t("chat_placeholder", lang))
    final_prompt = pending_prompt or user_typed

    if final_prompt:
        prev_hist = list(st.session_state["chat_messages"])
        st.session_state["chat_messages"].append(
            {"role": "user", "content": final_prompt, "chart": None, "source": None}
        )
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(final_prompt)

        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            with st.spinner("MoneyLens AI đang trả lời..." if lang == "vi" else "MoneyLens AI is thinking..."):
                result = ask_advisor(
                    question=final_prompt,
                    df=df,
                    selected_month=selected_month,
                    monthly_budget=monthly_budget,
                    api_key=gemini_key,
                    history=prev_hist,
                    lang=lang,
                    fixed_expenses=fixed_expenses,
                )
            st.markdown(result["answer"])
            if result.get("chart") is not None:
                c_idx = len(st.session_state["chat_messages"])
                st.plotly_chart(result["chart"], key=f"advisor_chart_live_{c_idx}", config={"displayModeBar": False})
            if result.get("source"):
                st.caption(f"{'Nguồn phân tích' if lang == 'vi' else 'Source'}: {result['source']}")

        st.session_state["chat_messages"].append(
            {
                "role": "assistant",
                "content": result["answer"],
                "chart": result.get("chart"),
                "source": result.get("source", "MoneyLens AI"),
            }
        )
        if pending_prompt:
            st.rerun()
