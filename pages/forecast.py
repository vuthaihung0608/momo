"""Screen 3 – Financial Forecast (Dual Theme, VI/EN, Statsmodels SES & Interactive What-If Simulator)."""

from __future__ import annotations

import html
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.components import (
    render_ai_banner,
    render_alert_item,
    render_kpi_card,
    render_section_header,
)
from ui.i18n import cat_label, t
from ui.service_adapter import forecast_cashflow, load_fixed_expenses
from ui.theme import apply_plotly_theme, format_vnd, get_palette


def render(
    df: pd.DataFrame,
    selected_month: str,
    monthly_budget: float,
    theme_mode: str = "light",
    lang: str = "vi",
    user: dict | None = None,
) -> None:
    p = get_palette(theme_mode)

    for k, default in (
        ("scen_cut_food", 0),
        ("scen_cut_shopping", 0),
        ("scen_cut_ent", 0),
        ("scen_cancel_subs", False),
        ("scen_extra_cost", 0),
        ("scen_extra_name", "Mua laptop mới"),
    ):
        if k not in st.session_state:
            st.session_state[k] = default

    st.markdown(
        f"""
        <h1 class="ml-page-title">{html.escape(t('fc_title', lang))}</h1>
        <div class="ml-page-subtitle">{html.escape(t('fc_sub', lang))}</div>
        <div style="height:12px;"></div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Chưa có dữ liệu để chạy dự báo." if lang == "vi" else "No data available for forecasting.")
        return

    fixed_expenses = load_fixed_expenses(user["id"]) if user else []
    forecast = forecast_cashflow(
        df=df,
        monthly_budget=monthly_budget,
        cut_food_pct=int(st.session_state["scen_cut_food"]),
        cut_shopping_pct=int(st.session_state["scen_cut_shopping"]),
        cut_entertainment_pct=int(st.session_state["scen_cut_ent"]),
        extra_one_time_expense=float(st.session_state["scen_extra_cost"]),
        extra_expense_label=str(st.session_state["scen_extra_name"] or "Khoản chi dự kiến"),
        cancel_subscriptions=bool(st.session_state["scen_cancel_subs"]),
        fixed_expenses=fixed_expenses,
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card(
            label=t("kpi_eom", lang),
            value=format_vnd(forecast["eom_scenario_balance"]),
            icon_name="trending_up",
            icon_color=p["success"] if forecast["eom_scenario_balance"] >= 0 else p["danger"],
            icon_bg=p["success_soft"] if forecast["eom_scenario_balance"] >= 0 else p["danger_soft"],
            pill_text=forecast["status_label"],
            pill_variant=forecast["status_variant"],
            footer_note=forecast["eom_date"].strftime("%d/%m/%Y"),
            sparkline="up" if forecast["eom_scenario_balance"] >= 0 else "down",
        )
    with k2:
        render_kpi_card(
            label=t("kpi_next_mo", lang),
            value=format_vnd(forecast["next_month_expense_scen"]),
            icon_name="calendar",
            icon_color=p["primary"],
            icon_bg=p["primary_soft"],
            pill_text=f"{format_vnd(forecast['adj_daily_var'], compact=True)}/day",
            pill_variant="primary",
            footer_note=f"Base: {format_vnd(forecast['next_month_expense_base'], compact=True)}",
        )
    with k3:
        risk = int(forecast["overrun_risk"])
        rv = "danger" if risk >= 75 else ("warning" if risk >= 45 else "success")
        render_kpi_card(
            label=t("kpi_risk", lang),
            value=f"{risk}%",
            icon_name="alert_triangle",
            icon_color=p[rv],
            icon_bg=p[f"{rv}_soft"],
            pill_text=("Rủi ro cao" if lang == "vi" else "High Risk") if risk >= 75 else ("Cần chú ý" if risk >= 45 else "On Track"),
            pill_variant=rv,
            footer_note=format_vnd(monthly_budget, compact=True),
        )
    with k4:
        bills_df = forecast["upcoming_bills"]
        render_kpi_card(
            label=t("kpi_upcoming", lang),
            value=format_vnd(forecast["upcoming_bills_total"]),
            icon_name="receipt",
            icon_color=p["warning"],
            icon_bg=p["warning_soft"],
            pill_text=f"{len(bills_df)} bills / 30d",
            pill_variant="warning",
            footer_note="Auto-deducted",
        )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    col_chart, col_lab = st.columns([1.55, 1.0])
    with col_chart:
        with st.container(border=True):
            bt = forecast.get("backtest_metrics", {})
            render_section_header(
                "Biểu đồ dự báo số dư dòng tiền (30 ngày)" if lang == "vi" else "Projected Cash Balance (30 Days)",
                f"{forecast.get('model_name', 'Statsmodels SES')} · Backtest MAE ~{format_vnd(bt.get('mae_daily', 0))}/day",
                icon_name="trending_up",
                theme_mode=theme_mode,
            )

            tl = forecast["timeline"].copy()
            hist = tl.loc[tl["segment"] == "historical"]
            fut = tl.loc[tl["segment"] == "forecast"]
            today_dt = forecast["latest_date"]
            fut_c = pd.concat([hist.tail(1), fut], ignore_index=True)

            pos_y = np.maximum(fut_c["scenario_balance"].to_numpy(), 0.0)
            neg_y = np.minimum(fut_c["scenario_balance"].to_numpy(), 0.0)

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=pd.concat([fut_c["date"], fut_c["date"][::-1]]),
                    y=pd.concat([fut_c["upper_band"], fut_c["lower_band"][::-1]]),
                    fill="toself", fillcolor="rgba(37, 99, 235, 0.08)",
                    line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip", name="90% CI",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=hist["date"], y=hist["base_balance"], mode="lines",
                    name="Lịch sử" if lang == "vi" else "History",
                    line=dict(color=p["success"], width=2.4), fill="tozeroy",
                    fillcolor="rgba(16, 185, 129, 0.18)",
                )
            )
            fig.add_trace(go.Scatter(x=fut_c["date"], y=pos_y, mode="lines", line=dict(width=0), fill="tozeroy", fillcolor="rgba(16, 185, 129, 0.25)", hoverinfo="skip", showlegend=False))
            if (neg_y < 0).any():
                fig.add_trace(go.Scatter(x=fut_c["date"], y=neg_y, mode="lines", line=dict(width=0), fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.35)", hoverinfo="skip", name="Deficit (<0)"))
            fig.add_trace(
                go.Scatter(
                    x=fut_c["date"], y=fut_c["scenario_balance"], mode="lines",
                    name="Dự báo" if lang == "vi" else "Forecast",
                    line=dict(color=p["ink"], width=2.6),
                )
            )

            scen_active = (
                st.session_state["scen_cut_food"] > 0 or st.session_state["scen_cut_shopping"] > 0
                or st.session_state["scen_cut_ent"] > 0 or st.session_state["scen_cancel_subs"]
                or st.session_state["scen_extra_cost"] > 0
            )
            if scen_active:
                fig.add_trace(go.Scatter(x=fut_c["date"], y=fut_c["base_balance"], mode="lines", name="Base", line=dict(color="#94A3B8", width=2, dash="dot")))

            fig.add_hline(y=0, line_color="#94A3B8", line_width=1.2)
            today_iso = pd.Timestamp(today_dt).strftime("%Y-%m-%d")
            fig.add_shape(type="line", x0=today_iso, x1=today_iso, y0=0, y1=1, xref="x", yref="paper", line=dict(color=p["primary"], width=1.6, dash="dash"))
            fig.add_annotation(x=today_iso, y=1.04, xref="x", yref="paper", text=f"<b>{'Hôm nay' if lang == 'vi' else 'Today'} ({pd.Timestamp(today_dt).strftime('%d/%m')})</b>", showarrow=False, font=dict(size=11, color=p["primary"]))

            apply_plotly_theme(fig, height=340, theme_mode=theme_mode)
            fig.update_yaxes(tickformat=",.0f")
            st.plotly_chart(fig, config={"displayModeBar": False})

        bullets_html = "".join(f"<li style='margin-bottom:4px;'>{pt}</li>" for pt in forecast["explanation_points"])
        bullets_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", bullets_html)
        render_ai_banner(
            title="Giải thích xu hướng dự báo" if lang == "vi" else "Forecast Insights",
            body_html=f"<ul style='margin:6px 0 0 18px;padding:0;'>{bullets_html}</ul>",
            icon_name="cpu",
            theme_mode=theme_mode,
        )

    with col_lab:
        with st.container(border=True):
            render_section_header("What-If Simulator", "Mô phỏng cắt giảm hoặc khoản mua lớn." if lang == "vi" else "Simulate spending cuts or big purchases.", icon_name="target", theme_mode=theme_mode)
            p1, p2, p3 = st.columns(3)
            with p1:
                if st.button("Tiết kiệm" if lang == "vi" else "Save", icon=":material/savings:", key="fc_p_save", width="stretch"):
                    st.session_state["scen_cut_food"] = 20
                    st.session_state["scen_cut_shopping"] = 35
                    st.session_state["scen_cut_ent"] = 20
                    st.session_state["scen_cancel_subs"] = True
                    st.session_state["scen_extra_cost"] = 0
                    st.rerun()
            with p2:
                if st.button("Laptop 15tr", icon=":material/laptop_mac:", key="fc_p_lap", width="stretch"):
                    st.session_state["scen_cut_food"] = 0
                    st.session_state["scen_cut_shopping"] = 0
                    st.session_state["scen_cut_ent"] = 0
                    st.session_state["scen_cancel_subs"] = False
                    st.session_state["scen_extra_cost"] = 15_000_000
                    st.session_state["scen_extra_name"] = "Mua Laptop 15 triệu"
                    st.rerun()
            with p3:
                if st.button("Mặc định" if lang == "vi" else "Reset", icon=":material/restart_alt:", key="fc_p_rst", width="stretch"):
                    st.session_state["scen_cut_food"] = 0
                    st.session_state["scen_cut_shopping"] = 0
                    st.session_state["scen_cut_ent"] = 0
                    st.session_state["scen_cancel_subs"] = False
                    st.session_state["scen_extra_cost"] = 0
                    st.rerun()

            st.slider("Giảm Ăn uống (%)" if lang == "vi" else "Cut Food (%)", 0, 50, key="scen_cut_food", step=5)
            st.slider("Giảm Mua sắm (%)" if lang == "vi" else "Cut Shopping (%)", 0, 70, key="scen_cut_shopping", step=5)
            st.slider("Giảm Giải trí (%)" if lang == "vi" else "Cut Entertainment (%)", 0, 60, key="scen_cut_ent", step=5)
            st.toggle("Tạm hủy gói định kỳ (Spotify, Netflix...)" if lang == "vi" else "Pause Entertainment Subs", key="scen_cancel_subs")
            st.divider()
            st.text_input("Khoản mua lớn dự kiến" if lang == "vi" else "Planned Purchase", key="scen_extra_name")
            st.number_input("Số tiền (VND)" if lang == "vi" else "Amount (VND)", min_value=0, max_value=100_000_000, step=500_000, key="scen_extra_cost")

            d30 = forecast["savings_vs_base_30d"]
            dc = p["success_dark"] if d30 >= 0 else p["danger_dark"]
            dbg = p["success_soft"] if d30 >= 0 else p["danger_soft"]
            dbd = p["success_border"] if d30 >= 0 else p["danger_border"]
            st.markdown(
                f"""
                <div style="background:{dbg};border:1px solid {dbd};border-radius:12px;padding:12px 14px;margin-top:8px;">
                    <div style="font-size:0.76rem;font-weight:600;color:{p['ink_secondary']};">{'Tác động sau 30 ngày' if lang == 'vi' else '30-Day Scenario Impact'}</div>
                    <div class="ml-num" style="font-size:1.22rem;font-weight:700;color:{dc};margin-top:2px;">{format_vnd(d30, show_sign=True)}</div>
                    <div style="font-size:0.75rem;color:{p['muted']};margin-top:3px;">30d: <strong>{format_vnd(forecast['balance_30d_scenario'])}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.container(border=True):
        render_section_header("Lịch hóa đơn định kỳ sắp tới (30 ngày)" if lang == "vi" else "Upcoming Recurring Bills (30 Days)", "", icon_name="calendar", theme_mode=theme_mode)
        bills_df = forecast["upcoming_bills"]
        if bills_df.empty:
            st.info("Chưa có hóa đơn dự kiến.")
        else:
            bc1, bc2 = st.columns(2)
            for idx, r in bills_df.iterrows():
                col = bc1 if idx % 2 == 0 else bc2
                due = pd.Timestamp(r["due_date"]).strftime("%d/%m/%Y")
                with col:
                    render_alert_item(
                        title=str(r["merchant"]),
                        subtitle=f"{due} · {cat_label(r['category'], lang)}",
                        amount_str=format_vnd(r["amount"]),
                        badge_text="Subscription" if r["is_subscription"] else ("Cố định" if lang == "vi" else "Fixed"),
                        variant="warning" if r["is_subscription"] else "primary",
                        theme_mode=theme_mode,
                    )
