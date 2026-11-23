"""Dual-Theme UI Components, Mini Sparklines, Printable Report Export & Floating Circular AI Help Widget."""

from __future__ import annotations

import html
from datetime import datetime
import pandas as pd
import streamlit as st

from src.help_assistant import answer_help_question
from ui.i18n import cat_label, t
from ui.icons import icon_svg, sparkline_svg
from ui.theme import format_vnd, get_palette


def render_kpi_card(
    label: str,
    value: str,
    icon_name: str,
    icon_color: str,
    icon_bg: str,
    pill_text: str | None = None,
    pill_variant: str = "neutral",
    footer_note: str = "",
    sparkline: str | None = None,
) -> None:
    """Render reference-mockup KPI card with icon badge, tabular VND value, trend pill, and optional sparkline."""
    pill_html = f'<span class="ml-pill ml-pill-{pill_variant}">{html.escape(pill_text)}</span>' if pill_text else ""
    note_html = f'<div class="ml-kpi-note">{html.escape(footer_note)}</div>' if footer_note else ""
    spark_html = sparkline_svg(sparkline) if sparkline in ("up", "down") else ""
    svg = icon_svg(icon_name, color=icon_color, size=16)

    card_html = (
        f'<div class="ml-kpi-card">'
        f'<div class="ml-kpi-top">'
        f'<span class="ml-kpi-label">{html.escape(label)}</span>'
        f'<div class="ml-kpi-icon" style="background:{icon_bg};">{svg}</div>'
        f'</div>'
        f'<div class="ml-kpi-value">{html.escape(value)}</div>'
        f'<div class="ml-kpi-bottom">'
        f'<div class="ml-kpi-meta">{pill_html}{note_html}</div>'
        f'<div>{spark_html}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_budget_progress_card(
    spent: float,
    budget: float,
    theme_mode: str = "light",
    lang: str = "vi",
) -> None:
    """Render budget utilization card with red/amber/emerald progress bar matching reference mockup."""
    p = get_palette(theme_mode)
    pct = (spent / budget * 100.0) if budget > 0 else 0.0
    clamped = min(pct, 100.0)
    remaining = budget - spent

    if pct >= 100:
        bar_color = p["danger"]
        icon_bg = p["danger_soft"]
        pill_class = "danger"
        status_text = f"{t('over_budget', lang)} {format_vnd(abs(remaining))}"
    elif pct >= 80:
        bar_color = p["warning"]
        icon_bg = p["warning_soft"]
        pill_class = "warning"
        status_text = f"{t('near_limit', lang)} ({pct:.0f}%)"
    else:
        bar_color = p["success"]
        icon_bg = p["success_soft"]
        pill_class = "success"
        status_text = f"{t('remaining', lang)} {format_vnd(remaining)}"

    svg = icon_svg("target", color=bar_color, size=16)
    st.markdown(
        f"""
        <div class="ml-kpi-card">
            <div class="ml-kpi-top">
                <span class="ml-kpi-label">{html.escape(t('kpi_budget', lang))}</span>
                <div class="ml-kpi-icon" style="background:{icon_bg};">{svg}</div>
            </div>
            <div class="ml-kpi-value">{pct:.0f}% <span style="font-size:0.84rem;font-weight:500;color:{p['muted']};">/ {html.escape(format_vnd(budget))}</span></div>
            <div class="ml-progress-track">
                <div class="ml-progress-fill" style="width:{clamped:.1f}%;background:{bar_color};"></div>
            </div>
            <div class="ml-kpi-bottom">
                <span class="ml-pill ml-pill-{pill_class}">{html.escape(status_text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ai_banner(
    title: str,
    body_html: str,
    icon_name: str = "sparkles",
    theme_mode: str = "light",
) -> None:
    """Render AI Insight highlight callout banner."""
    p = get_palette(theme_mode)
    svg = icon_svg(icon_name, color=p["primary"], size=16)
    st.markdown(
        f"""
        <div class="ml-ai-banner">
            <div class="ml-ai-banner-title">{svg}{html.escape(title)}</div>
            <div class="ml-ai-banner-body">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(
    title: str,
    caption: str = "",
    icon_name: str | None = None,
    theme_mode: str = "light",
) -> None:
    """Render section title + caption with crisp vector icon."""
    p = get_palette(theme_mode)
    ic = icon_svg(icon_name, color=p["primary"], size=16) if icon_name else ""
    cap_html = f'<p class="ml-card-caption">{html.escape(caption)}</p>' if caption else ""
    st.markdown(
        f'<div style="margin-bottom:6px;"><div class="ml-card-title">{ic}<span>{html.escape(title)}</span></div>{cap_html}</div>',
        unsafe_allow_html=True,
    )


def render_alert_item(
    title: str,
    subtitle: str,
    amount_str: str,
    badge_text: str,
    variant: str = "danger",
    theme_mode: str = "light",
) -> None:
    """Render anomaly, recurring bill, or micro-spending item card."""
    p = get_palette(theme_mode)
    st.markdown(
        f"""
        <div class="ml-list-item ml-list-item-{variant}">
            <div style="min-width:0;flex:1;">
                <div style="font-weight:600;font-size:0.88rem;color:{p['ink']};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {html.escape(title)}
                </div>
                <div style="font-size:0.77rem;color:{p['muted']};margin-top:2px;line-height:1.35;">
                    {html.escape(subtitle)}
                </div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
                <div class="ml-num" style="font-weight:700;font-size:0.88rem;color:{p['ink']};">{html.escape(amount_str)}</div>
                <span class="ml-pill ml-pill-{variant}" style="margin-top:3px;">{html.escape(badge_text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_printable_report_html(
    user_name: str,
    period_label: str,
    metrics: dict,
    spending: dict,
    forecast: dict,
    monthly_budget: float,
    lang: str = "vi",
) -> bytes:
    """Generate a clean print-to-PDF HTML financial summary report."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    bd: pd.DataFrame = spending["category_breakdown"]
    rows_html = ""
    if not bd.empty:
        for _, r in bd.iterrows():
            rows_html += (
                f"<tr><td>{html.escape(cat_label(r['category'], lang))}</td>"
                f"<td>{int(r['tx_count'])}</td>"
                f"<td style='text-align:right;font-weight:600'>{html.escape(format_vnd(r['amount']))}</td>"
                f"<td style='text-align:right'>{r['share_pct']:.1f}%</td></tr>"
            )
    doc = f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="UTF-8"><title>MoneyLens AI Report - {html.escape(period_label)}</title>
<style>
  body {{ font-family: 'IBM Plex Sans', Arial, sans-serif; max-width: 820px; margin: 28px auto; color: #0F172A; line-height: 1.5; }}
  .head {{ display:flex; justify-content:space-between; border-bottom:2px solid #1E40AF; padding-bottom:12px; margin-bottom:20px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px; }}
  .box {{ border:1px solid #E2E8F0; border-radius:10px; padding:12px; background:#F8FAFC; }}
  .lbl {{ font-size:11px; color:#64748B; text-transform:uppercase; font-weight:700; }}
  .val {{ font-size:18px; font-weight:700; margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:13px; }}
  th, td {{ padding:8px 10px; border-bottom:1px solid #E2E8F0; text-align:left; }}
  th {{ background:#F1F5F9; }}
  .btn {{ background:#1E40AF; color:#fff; border:none; padding:8px 16px; border-radius:8px; cursor:pointer; }}
  @media print {{ .no-print {{ display:none; }} }}
</style></head><body>
<div class="head">
  <div><h2 style="margin:0;color:#1E40AF">MoneyLens AI · Báo cáo Tài chính</h2>
  <div style="font-size:13px;color:#475569">{html.escape(user_name)} · {html.escape(period_label)} · Xuất lúc {now_str}</div></div>
  <button class="btn no-print" onclick="window.print()">In / Lưu PDF</button>
</div>
<div class="grid">
  <div class="box"><div class="lbl">{html.escape(t('kpi_income', lang))}</div><div class="val">{html.escape(format_vnd(metrics['income']))}</div></div>
  <div class="box"><div class="lbl">{html.escape(t('kpi_expense', lang))}</div><div class="val">{html.escape(format_vnd(metrics['expense']))}</div></div>
  <div class="box"><div class="lbl">{html.escape(t('kpi_balance', lang))}</div><div class="val">{html.escape(format_vnd(metrics['cumulative_balance']))}</div></div>
  <div class="box"><div class="lbl">{html.escape(t('kpi_eom', lang))}</div><div class="val">{html.escape(format_vnd(forecast['eom_scenario_balance']))}</div></div>
</div>
<h3>Phân bổ chi tiêu theo danh mục</h3>
<table><thead><tr><th>Danh mục</th><th>Số giao dịch</th><th style="text-align:right">Tổng chi</th><th style="text-align:right">Tỷ trọng</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<p style="margin-top:20px;font-size:13px;color:#475569">Ngân sách mục tiêu: <b>{html.escape(format_vnd(monthly_budget))}</b> · Mô hình dự báo: <b>{html.escape(forecast.get('model_name', 'Statsmodels SES'))}</b></p>
</body></html>"""
    return doc.encode("utf-8")


def render_floating_help_chat(lang: str = "vi", api_key: str = "") -> None:
    """Render the bottom-right floating circular AI Support & Product Guide chat widget."""
    if "help_messages" not in st.session_state:
        st.session_state["help_messages"] = [
            {"role": "assistant", "content": t("help_welcome", lang)}
        ]

    with st.container():
        st.markdown('<div class="ml-fab-marker"></div>', unsafe_allow_html=True)
        with st.popover("", icon=":material/support_agent:", help=t("help_title", lang)):
            st.markdown(f"**{t('help_title', lang)}**")
            st.caption(t("help_sub", lang))

            # Quick guide chips inside popover
            quick_help = (
                [
                    "Cách nhập 'Xăng 100k' & chụp bill?",
                    "Lấy API ngân hàng có phạm pháp không?",
                    "Cách bật Dark Mode / Đổi ngôn ngữ?",
                ]
                if lang == "vi"
                else [
                    "How to log 'Gas 100k' & scan bills?",
                    "Is bank API sync legal in Vietnam?",
                    "How to toggle Dark Mode & language?",
                ]
            )
            chosen_help = None
            for idx, qh in enumerate(quick_help):
                if st.button(qh, key=f"fab_q_{idx}", width="stretch"):
                    chosen_help = qh

            st.divider()
            chat_box = st.container(height=240, border=False)
            with chat_box:
                for msg in st.session_state["help_messages"][-8:]:
                    av = ":material/smart_toy:" if msg["role"] == "assistant" else ":material/person:"
                    with st.chat_message(msg["role"], avatar=av):
                        st.markdown(msg["content"])

            with st.form("fab_help_form", clear_on_submit=True):
                c_in, c_btn = st.columns([3.2, 1.0])
                with c_in:
                    typed_q = st.text_input(
                        "help_q",
                        placeholder=t("help_input_ph", lang),
                        label_visibility="collapsed",
                    )
                with c_btn:
                    submitted = st.form_submit_button(t("help_send", lang), width="stretch")

            final_q = chosen_help or (typed_q.strip() if submitted and typed_q.strip() else None)
            if final_q:
                prev_hist = list(st.session_state["help_messages"])
                st.session_state["help_messages"].append({"role": "user", "content": final_q})
                reply = answer_help_question(final_q, lang=lang, api_key=api_key, history=prev_hist)
                st.session_state["help_messages"].append({"role": "assistant", "content": reply})
                st.rerun()
