"""Screen 1 – Financial Overview (Reference-Mockup Layout, Dual Theme, VI/EN, Sparklines, Report Export)."""

from __future__ import annotations

import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.components import (
    build_printable_report_html,
    render_ai_banner,
    render_budget_progress_card,
    render_kpi_card,
    render_section_header,
)
from ui.i18n import cat_label, fmt_month_label, t
from ui.service_adapter import (
    analyze_spending,
    compute_overview_metrics,
    delete_transactions_bulk,
    filter_by_month,
    forecast_cashflow,
    load_fixed_expenses,
)
from ui.theme import apply_plotly_theme, build_clean_donut_figure, format_vnd, get_palette


def render(
    df: pd.DataFrame,
    selected_month: str,
    monthly_budget: float,
    theme_mode: str = "light",
    lang: str = "vi",
    user: dict | None = None,
) -> None:
    p = get_palette(theme_mode)
    period_label = fmt_month_label(selected_month, lang=lang, is_latest=False)
    user_name = (user or {}).get("full_name", "MoneyLens User")

    metrics = compute_overview_metrics(df, selected_month)
    fixed_expenses = load_fixed_expenses(user["id"]) if user else []
    spending = analyze_spending(df, selected_month, fixed_expenses=fixed_expenses)
    forecast = (
        forecast_cashflow(df, monthly_budget=monthly_budget, fixed_expenses=fixed_expenses)
        if not df.empty
        else {"eom_scenario_balance": 0, "model_name": "Statsmodels SES"}
    )

    # Header Row matching reference screenshot: Title + Subtitle (left) | Refresh + Export Report (right)
    h_left, h_btn1, h_btn2 = st.columns([2.9, 0.85, 0.98], vertical_alignment="center")
    with h_left:
        goal_hint = (user or {}).get("financial_goal", "")
        sub_txt = (
            f"{t('ov_sub', lang)} · {user_name}"
            + (f" ({goal_hint})" if goal_hint else "")
        )
        st.markdown(
            f"""
            <h1 class="ml-page-title">{html.escape(t('ov_title', lang))} • {html.escape(period_label)}</h1>
            <div class="ml-page-subtitle">{html.escape(sub_txt)}</div>
            """,
            unsafe_allow_html=True,
        )
    with h_btn1:
        if st.button(t("refresh_data", lang), icon=":material/refresh:", key="ov_refresh", width="stretch"):
            st.session_state["force_reload_db"] = True
            st.rerun()
    with h_btn2:
        report_bytes = build_printable_report_html(
            user_name=user_name,
            period_label=period_label,
            metrics=metrics,
            spending=spending,
            forecast=forecast,
            monthly_budget=monthly_budget,
            lang=lang,
        )
        st.download_button(
            label=t("export_report", lang),
            icon=":material/download:",
            data=report_bytes,
            file_name=f"MoneyLens_Report_{selected_month}.html",
            mime="text/html",
            key="ov_export_pdf",
            width="stretch",
        )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    if df.empty:
        st.info(
            "Tài khoản của bạn đang trắng tinh (0 giao dịch). Bạn có thể bắt đầu bằng cách: nhập nhanh `Xăng 100k`, chụp ảnh hóa đơn ở khung bên trái, bật **Bank Sync qua Email** để AI tự động quét, hoặc vào **Phân tích chi tiêu** để thêm khoản chi cố định hàng tháng!"
            if lang == "vi"
            else "Your workspace starts completely clean (0 transactions). Start by typing `Gas 100k`, scanning a receipt, enabling **Bank Email Auto-Sync**, or adding fixed monthly expenses under **Spending Insights**!"
        )
        return

    cur_df = filter_by_month(df, selected_month)
    inc_delta = metrics["income_delta_pct"]
    exp_delta = metrics["expense_delta_pct"]

    inc_pill = f"{inc_delta:+.1f}% {t('vs_prev', lang)}" if inc_delta is not None else f"{len(cur_df[cur_df['type']=='income'])} {t('income_opt', lang).lower()}"
    inc_variant = "success" if (inc_delta is None or inc_delta >= 0) else "warning"

    exp_pill = f"{exp_delta:+.1f}% {t('vs_prev', lang)}" if exp_delta is not None else f"{len(cur_df[cur_df['type']=='expense'])} {t('expense_opt', lang).lower()}"
    exp_variant = "danger" if (exp_delta is not None and exp_delta > 10) else ("success" if (exp_delta is not None and exp_delta < 0) else "neutral")

    net_pill = f"{t('saving_rate', lang)} {metrics['savings_rate']:.1f}%"
    net_variant = "success" if metrics["net_balance"] >= 0 else "danger"

    # 4 KPI Cards with Mini Sparklines (matching exact reference screenshot!)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card(
            label=t("kpi_income", lang),
            value=format_vnd(metrics["income"]),
            icon_name="arrow_down_left",
            icon_color=p["success"],
            icon_bg=p["success_soft"],
            pill_text=inc_pill,
            pill_variant=inc_variant,
            footer_note=period_label,
            sparkline="up",
        )
    with k2:
        render_kpi_card(
            label=t("kpi_expense", lang),
            value=format_vnd(metrics["expense"]),
            icon_name="credit_card",
            icon_color=p["danger"],
            icon_bg=p["danger_soft"],
            pill_text=exp_pill,
            pill_variant=exp_variant,
            footer_note=f"{t('ml_tagged', lang)}: {metrics['auto_cat_count']} {t('rows_unit', lang)}",
            sparkline="down",
        )
    with k3:
        render_kpi_card(
            label=t("kpi_balance", lang),
            value=format_vnd(metrics["cumulative_balance"]),
            icon_name="landmark",
            icon_color=p["primary"],
            icon_bg=p["primary_soft"],
            pill_text=net_pill,
            pill_variant=net_variant,
            footer_note=f"{t('net_period', lang)}: {format_vnd(metrics['net_balance'], show_sign=True, compact=True)}",
            sparkline="up" if metrics["net_balance"] >= 0 else "down",
        )
    with k4:
        eff_budget = monthly_budget if selected_month != "ALL" else monthly_budget * max(df["year_month"].nunique(), 1)
        render_budget_progress_card(spent=metrics["expense"], budget=eff_budget, theme_mode=theme_mode, lang=lang)

    # AI Quick Insight Banner
    top_cat_lbl = cat_label(spending["top_category"], lang)
    spike_txt = ""
    if spending["spikes"]:
        sp0 = spending["spikes"][0]
        if lang == "en":
            spike_txt = f" Notably, <strong>{cat_label(sp0['category'], lang)}</strong> surged <strong>+{sp0['change_pct']:.0f}%</strong> vs last month."
        else:
            spike_txt = f" Đáng chú ý, nhóm <strong>{cat_label(sp0['category'], lang)}</strong> tăng <strong>+{sp0['change_pct']:.0f}%</strong> so với tháng trước."

    if lang == "en":
        banner_body = (
            f"In <strong>{html.escape(period_label)}</strong>, you spent <strong>{format_vnd(metrics['expense'])}</strong> "
            f"(net cash flow <strong>{format_vnd(metrics['net_balance'], show_sign=True)}</strong>). "
            f"Largest category: <strong>{html.escape(top_cat_lbl)}</strong> (<strong>{spending['top_category_share']:.1f}%</strong>).{spike_txt}"
        )
    else:
        banner_body = (
            f"Trong <strong>{html.escape(period_label)}</strong>, bạn đã chi <strong>{format_vnd(metrics['expense'])}</strong> "
            f"(dòng tiền ròng <strong>{format_vnd(metrics['net_balance'], show_sign=True)}</strong>). "
            f"Danh mục chiếm tỷ trọng lớn nhất là <strong>{html.escape(top_cat_lbl)}</strong> (<strong>{spending['top_category_share']:.1f}%</strong>).{spike_txt}"
        )

    render_ai_banner(title=t("ai_quick_title", lang), body_html=banner_body, icon_name="sparkles", theme_mode=theme_mode)

    # 2-Column Charts Row (Cash Flow Left | Donut + Right Legend)
    c_left, c_right = st.columns([1.22, 1.0])

    with c_left:
        with st.container(border=True):
            render_section_header(t("chart_cf_title", lang), t("chart_cf_sub", lang), icon_name="trending_up", theme_mode=theme_mode)
            chart_mode = st.segmented_control(
                "cf_mode",
                options=[t("mode_balance", lang), t("mode_inc_exp", lang)],
                default=t("mode_balance", lang),
                label_visibility="collapsed",
                key="ov_cf_mode",
            )

            if chart_mode == t("mode_inc_exp", lang):
                if selected_month == "ALL":
                    grouped = (
                        cur_df.groupby(["year_month", "type"], as_index=False)["amount"]
                        .sum()
                        .pivot(index="year_month", columns="type", values="amount")
                        .fillna(0)
                        .reset_index()
                    )
                    x_vals = grouped["year_month"]
                else:
                    tmp = cur_df.copy()
                    wk_pfx = "W" if lang == "en" else "Tuần "
                    tmp["wk"] = wk_pfx + ((tmp["date"].dt.day - 1) // 7 + 1).astype(str)
                    grouped = (
                        tmp.groupby(["wk", "type"], as_index=False)["amount"]
                        .sum()
                        .pivot(index="wk", columns="type", values="amount")
                        .fillna(0)
                        .reset_index()
                    )
                    x_vals = grouped["wk"]
                inc_s = grouped["income"] if "income" in grouped.columns else pd.Series([0] * len(grouped))
                exp_s = grouped["expense"] if "expense" in grouped.columns else pd.Series([0] * len(grouped))
                fig_cf = go.Figure()
                fig_cf.add_trace(go.Bar(name=t("income_opt", lang), x=x_vals, y=inc_s, marker=dict(color=p["success"], cornerradius=6)))
                fig_cf.add_trace(go.Bar(name=t("expense_opt", lang), x=x_vals, y=exp_s, marker=dict(color=p["danger"], cornerradius=6)))
                fig_cf.update_layout(barmode="group", bargap=0.28)
                apply_plotly_theme(fig_cf, height=275, show_legend=True, theme_mode=theme_mode)
                st.plotly_chart(fig_cf, config={"displayModeBar": False})
            else:
                daily = cur_df.groupby("date", as_index=False)["signed_amount"].sum().sort_values("date")
                opening = (
                    float(df.loc[df["year_month"] < selected_month, "signed_amount"].sum())
                    if selected_month != "ALL"
                    else 0.0
                )
                daily["balance"] = opening + daily["signed_amount"].cumsum()
                fig_bal = go.Figure()
                fig_bal.add_trace(
                    go.Scatter(
                        x=daily["date"],
                        y=daily["balance"],
                        mode="lines+markers",
                        line=dict(color=p["primary"], width=2.6, shape="spline"),
                        marker=dict(size=6, color=p["primary"]),
                        fill="tozeroy",
                        fillcolor="rgba(37, 99, 235, 0.12)",
                        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>%{y:,.0f} ₫<extra></extra>",
                    )
                )
                apply_plotly_theme(fig_bal, height=275, show_legend=False, theme_mode=theme_mode)
                fig_bal.update_yaxes(tickformat=",.0f")
                st.plotly_chart(fig_bal, config={"displayModeBar": False})

    with c_right:
        with st.container(border=True):
            render_section_header(t("chart_donut_title", lang), t("chart_donut_sub", lang), icon_name="pie_chart", theme_mode=theme_mode)
            bd = spending["category_breakdown"]
            if bd.empty:
                st.info("No expense data in this period.")
            else:
                fig_donut = build_clean_donut_figure(bd, spending["total_expense"], height=318, theme_mode=theme_mode, lang=lang)
                st.plotly_chart(fig_donut, config={"displayModeBar": False})

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Recent Transactions Table with Source & Transfer Memo
    with st.container(border=True):
        render_section_header(t("recent_tx_title", lang), t("recent_tx_sub", lang), icon_name="receipt", theme_mode=theme_mode)
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_q = st.text_input(t("search_tx", lang), placeholder="Highlands, Shopee, MBBank, Xăng...", key="ov_search")
        with f2:
            type_f = st.selectbox(t("filter_type", lang), options=[t("all_opt", lang), t("expense_opt", lang), t("income_opt", lang)], key="ov_type_f")
        with f3:
            avail_cats = sorted(cur_df["category"].unique().tolist())
            cat_f = st.selectbox(
                t("filter_cat", lang),
                options=["ALL"] + avail_cats,
                format_func=lambda c: t("all_opt", lang) if c == "ALL" else cat_label(c, lang),
                key="ov_cat_f",
            )

        filtered = cur_df.copy()
        if search_q.strip():
            mask = filtered["description"].str.contains(search_q.strip(), case=False, na=False)
            if "transfer_memo" in filtered.columns:
                mask = mask | filtered["transfer_memo"].astype(str).str.contains(search_q.strip(), case=False, na=False)
            filtered = filtered.loc[mask]
        if type_f == t("expense_opt", lang):
            filtered = filtered.loc[filtered["type"] == "expense"]
        elif type_f == t("income_opt", lang):
            filtered = filtered.loc[filtered["type"] == "income"]
        if cat_f != "ALL":
            filtered = filtered.loc[filtered["category"] == cat_f]

        filtered = filtered.sort_values("date", ascending=False)
        source_labels = {
            "quick_text": "Nhập nhanh" if lang == "vi" else "Quick Text",
            "bill_ocr": "Quét Bill AI" if lang == "vi" else "Bill OCR",
            "email_bank_sync": "Email AI Sync",
            "bank_sync": "Bank Sync",
            "sepay_webhook": "SePay Auto",
            "casso_webhook": "Casso Auto",
            "payos_webhook": "PayOS Auto",
            "auto_forward": "Notif Forward",
        }
        rows_html_parts = []
        for idx_r, row in filtered.head(60).iterrows():
            dt_s = pd.Timestamp(row["date"]).strftime("%d/%m/%Y")
            desc_s = html.escape(str(row["description"]))
            src_k = str(row.get("source_type", "bank_sync"))
            src_s = html.escape(source_labels.get(src_k, "Sync"))
            src_pill = (
                "success"
                if src_k in {"email_bank_sync", "sepay_webhook", "casso_webhook", "payos_webhook", "auto_forward"}
                else ("primary" if src_k == "bank_sync" else "neutral")
            )
            cat_s = html.escape(cat_label(str(row["category"]), lang))
            memo_raw = str(row.get("transfer_memo", "") or "").strip()
            memo_s = html.escape(memo_raw[:44] + ("…" if len(memo_raw) > 44 else "")) if memo_raw else "—"
            is_inc = str(row["type"]) == "income"
            amt_s = html.escape(format_vnd(row["amount"] if is_inc else -row["amount"], show_sign=True))
            amt_col = p["success"] if is_inc else p["danger"]
            rows_html_parts.append(
                f"<tr>"
                f"<td class='ml-num' style='white-space:nowrap;color:{p['muted']};'>{dt_s}</td>"
                f"<td style='font-weight:500;'>{desc_s}</td>"
                f"<td><span class='ml-pill ml-pill-{src_pill}'>{src_s}</span></td>"
                f"<td>{cat_s}</td>"
                f"<td style='color:{p['muted']};font-size:0.78rem;'>{memo_s}</td>"
                f"<td class='ml-num' style='text-align:right;font-weight:700;white-space:nowrap;color:{amt_col};'>{amt_s}</td>"
                f"</tr>"
            )

        h_date = "Ngày" if lang == "vi" else "Date"
        h_desc = "Mô tả" if lang == "vi" else "Description"
        h_src = "Nguồn" if lang == "vi" else "Channel"
        h_cat = "Danh mục" if lang == "vi" else "Category"
        h_memo = "Nội dung CK / Ghi chú" if lang == "vi" else "Memo"
        h_amt = "Số tiền (VND)" if lang == "vi" else "Amount (VND)"
        table_html = (
            f"<div class='ml-tx-table-wrap'><table class='ml-tx-table'>"
            f"<thead><tr><th>{h_date}</th><th>{h_desc}</th><th>{h_src}</th><th>{h_cat}</th><th>{h_memo}</th><th style='text-align:right;'>{h_amt}</th></tr></thead>"
            f"<tbody>{''.join(rows_html_parts)}</tbody></table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)
        st.caption(f"{len(filtered)} / {len(cur_df)} {t('tx_short', lang)} · {period_label}")

        # Delete mistaken transactions (1 or multiple in 1 click)
        if user and not filtered.empty and "id" in filtered.columns:
            with st.expander(
                "Xóa giao dịch nhập nhầm" if lang == "vi" else "Delete Mistaken Transactions",
                icon=":material/delete:",
            ):
                tx_options: list[int] = []
                tx_label_map: dict[int, str] = {}
                for _, r_del in filtered.head(80).iterrows():
                    tid = int(r_del["id"])
                    dt_lbl = pd.Timestamp(r_del["date"]).strftime("%d/%m/%Y")
                    amt_lbl = format_vnd(r_del["amount"] if r_del["type"] == "income" else -r_del["amount"], show_sign=True)
                    tx_options.append(tid)
                    tx_label_map[tid] = f"{dt_lbl} · {r_del['description']} ({amt_lbl})"

                selected_del_ids = st.multiselect(
                    "Chọn giao dịch cần xóa:" if lang == "vi" else "Select transaction(s) to delete:",
                    options=tx_options,
                    format_func=lambda i: tx_label_map.get(i, str(i)),
                    key="ov_delete_tx_ids",
                )
                if st.button(
                    f"Xóa {len(selected_del_ids)} giao dịch đã chọn" if lang == "vi" else f"Delete {len(selected_del_ids)} Selected Transaction(s)",
                    icon=":material/delete_forever:",
                    disabled=not selected_del_ids,
                    key="ov_confirm_delete_tx",
                ):
                    deleted_cnt = delete_transactions_bulk(selected_del_ids, user_id=user["id"])
                    st.session_state["force_reload_db"] = True
                    st.toast(
                        f"Đã xóa {deleted_cnt} giao dịch!" if lang == "vi" else f"Deleted {deleted_cnt} transaction(s)!"
                    )
                    st.rerun()
