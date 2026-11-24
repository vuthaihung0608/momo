"""Screen 2 – Spending Insights (Dual Theme, VI/EN, Overlap-Proof Donut, Micro-Spending & ML Eval)."""

from __future__ import annotations

import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.components import (
    render_ai_banner,
    render_alert_item,
    render_kpi_card,
    render_section_header,
)
from ui.i18n import cat_label, fmt_month_label, t
from ui.service_adapter import (
    analyze_spending,
    delete_fixed_expense,
    filter_by_month,
    get_ml_evaluation,
    insert_fixed_expense,
    load_fixed_expenses,
)
from ui.theme import (
    EXPENSE_CATEGORIES,
    apply_plotly_theme,
    build_clean_donut_figure,
    format_vnd,
    get_category_color,
    get_palette,
)


def _render_fixed_expenses_section(
    user: dict | None,
    recurring_df: pd.DataFrame,
    theme_mode: str,
    lang: str,
) -> None:
    """Render Recurring & User-Managed Fixed Monthly Expenses (Add / Delete)."""
    with st.container(border=True):
        render_section_header(
            "Chi tiêu cố định & Định kỳ hàng tháng" if lang == "vi" else "Fixed Monthly Expenses & Subscriptions",
            "Tự thêm hoặc xóa các khoản chi cố định (tiền phòng, Wifi, Spotify...) để tính vào dự báo."
            if lang == "vi"
            else "Add or delete monthly fixed expenses (rent, internet, subscriptions...) included in forecasts.",
            icon_name="repeat",
            theme_mode=theme_mode,
        )

        if user:
            with st.expander(
                "Thêm khoản chi tiêu cố định mới" if lang == "vi" else "Add Fixed Monthly Expense",
                icon=":material/add_circle:",
            ):
                with st.form("add_fixed_expense_form", clear_on_submit=True):
                    f_name = st.text_input(
                        "Tên khoản chi cố định" if lang == "vi" else "Fixed Expense Name",
                        placeholder="VD: Tiền thuê phòng, Wifi FPT, Spotify..." if lang == "vi" else "Ex: Rent, Internet, Spotify...",
                    )
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        f_amt = st.number_input(
                            "Số tiền / tháng (VND)" if lang == "vi" else "Amount / month (VND)",
                            min_value=1_000,
                            max_value=200_000_000,
                            value=500_000,
                            step=50_000,
                        )
                    with fc2:
                        f_day = st.number_input(
                            "Ngày đến hạn (1-31)" if lang == "vi" else "Due day (1-31)",
                            min_value=1,
                            max_value=31,
                            value=5,
                            step=1,
                        )
                    f_cat = st.selectbox(
                        "Danh mục" if lang == "vi" else "Category",
                        options=EXPENSE_CATEGORIES,
                        index=EXPENSE_CATEGORIES.index("Bills"),
                        format_func=lambda c: cat_label(c, lang),
                    )
                    add_btn = st.form_submit_button(
                        "Thêm khoản cố định" if lang == "vi" else "Add Fixed Expense",
                        icon=":material/add:",
                        type="primary",
                        width="stretch",
                    )
                if add_btn:
                    if not f_name.strip():
                        st.error("Vui lòng nhập tên khoản chi cố định." if lang == "vi" else "Please enter a name.")
                    else:
                        insert_fixed_expense(
                            user_id=user["id"],
                            name=f_name.strip(),
                            amount=float(f_amt),
                            category=f_cat,
                            due_day=int(f_day),
                        )
                        st.toast(
                            f"Đã thêm khoản cố định: {f_name.strip()}!"
                            if lang == "vi"
                            else f"Added fixed expense: {f_name.strip()}!"
                        )
                        st.rerun()

        if recurring_df.empty:
            st.info(
                "Chưa có khoản chi cố định nào. Bấm mục **Thêm khoản chi tiêu cố định mới** phía trên để tự thêm!"
                if lang == "vi"
                else "No fixed or recurring expenses yet. Click **Add Fixed Monthly Expense** above!"
            )
            return

        for idx, r in recurring_df.iterrows():
            due = pd.Timestamp(r["next_due_date"]).strftime("%d/%m/%Y")
            is_manual = bool(r.get("is_manual", False))
            fixed_id = r.get("fixed_id")
            var = "warning" if r["category"] == "Entertainment" else "primary"
            badge = (
                ("Cố định · Tự thêm" if lang == "vi" else "Fixed · Manual")
                if is_manual
                else ("Subscription" if r["category"] == "Entertainment" else ("Cố định · Tự nhận" if lang == "vi" else "Auto-Detected"))
            )
            if is_manual and user and pd.notna(fixed_id):
                c_item, c_del = st.columns([6.2, 0.85], vertical_alignment="center")
                with c_item:
                    render_alert_item(
                        title=str(r["merchant"]),
                        subtitle=f"{cat_label(r['category'], lang)} · Ngày {int(r['typical_day'])} (Next: {due})",
                        amount_str=f"{format_vnd(r['avg_amount'])}/mo",
                        badge_text=badge,
                        variant=var,
                        theme_mode=theme_mode,
                    )
                with c_del:
                    if st.button("", icon=":material/delete:", help="Xóa khoản cố định" if lang == "vi" else "Delete fixed expense", key=f"del_fix_{int(fixed_id)}_{idx}", width="stretch"):
                        delete_fixed_expense(int(fixed_id), user_id=user["id"])
                        st.toast("Đã xóa khoản chi cố định!" if lang == "vi" else "Fixed expense deleted!")
                        st.rerun()
            else:
                render_alert_item(
                    title=str(r["merchant"]),
                    subtitle=f"{cat_label(r['category'], lang)} · ~{format_vnd(r['annual_cost'], compact=True)}/yr · Next: {due}",
                    amount_str=f"{format_vnd(r['avg_amount'])}/mo",
                    badge_text=badge,
                    variant=var,
                    theme_mode=theme_mode,
                )


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

    st.markdown(
        f"""
        <h1 class="ml-page-title">{html.escape(t('sp_title', lang))} • {html.escape(period_label)}</h1>
        <div class="ml-page-subtitle">{html.escape(t('sp_sub', lang))}</div>
        <div style="height:12px;"></div>
        """,
        unsafe_allow_html=True,
    )

    fixed_expenses = load_fixed_expenses(user["id"]) if user else []
    spending = analyze_spending(df, selected_month, fixed_expenses=fixed_expenses)

    if df.empty:
        st.info(
            "Chưa có dữ liệu giao dịch chi tiêu. Bạn vẫn có thể tự thêm các **khoản chi cố định hàng tháng** ở khung bên dưới!"
            if lang == "vi"
            else "No spending transactions yet. You can already add your **fixed monthly expenses** below!"
        )
        _render_fixed_expenses_section(user, spending["recurring"], theme_mode, lang)
        return

    breakdown: pd.DataFrame = spending["category_breakdown"]
    anomalies_df: pd.DataFrame = spending["anomalies"]
    recurring_df: pd.DataFrame = spending["recurring"]
    micro = spending.get("micro_spending", {"count": 0, "total": 0.0, "share_pct": 0.0, "top_habits": pd.DataFrame()})
    spikes = spending["spikes"]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card(
            label=t("kpi_expense", lang),
            value=format_vnd(spending["total_expense"]),
            icon_name="credit_card",
            icon_color=p["danger"],
            icon_bg=p["danger_soft"],
            pill_text=f"{len(breakdown)} {'danh mục' if lang == 'vi' else 'categories'}",
            pill_variant="neutral",
            sparkline="down",
        )
    with k2:
        render_kpi_card(
            label=t("kpi_top_cat", lang),
            value=cat_label(spending["top_category"], lang),
            icon_name="award",
            icon_color=p["primary"],
            icon_bg=p["primary_soft"],
            pill_text=f"{spending['top_category_share']:.1f}%",
            pill_variant="primary",
            footer_note=format_vnd(spending["top_category_amount"], compact=True),
        )
    with k3:
        anom_cnt = len(anomalies_df)
        render_kpi_card(
            label=t("kpi_anomalies", lang),
            value=f"{anom_cnt} {t('tx_short', lang)}",
            icon_name="alert_triangle",
            icon_color=p["danger"] if anom_cnt > 0 else p["success"],
            icon_bg=p["danger_soft"] if anom_cnt > 0 else p["success_soft"],
            pill_text=("Cần xem lại" if lang == "vi" else "Review") if anom_cnt > 0 else ("Ổn định" if lang == "vi" else "Stable"),
            pill_variant="danger" if anom_cnt > 0 else "success",
            footer_note=format_vnd(anomalies_df["amount"].sum(), compact=True) if anom_cnt > 0 else "—",
        )
    with k4:
        render_kpi_card(
            label=t("kpi_recurring", lang),
            value=format_vnd(spending["recurring_monthly_total"]),
            icon_name="repeat",
            icon_color=p["warning"],
            icon_bg=p["warning_soft"],
            pill_text=f"{len(recurring_df)} {'khoản' if lang == 'vi' else 'items'}",
            pill_variant="warning",
            footer_note=f"~{format_vnd(spending['recurring_monthly_total'] * 12, compact=True)}/{'năm' if lang == 'vi' else 'yr'}",
        )

    if spikes:
        items_str = " · ".join(
            f"<strong>{html.escape(cat_label(s['category'], lang))}</strong> (+{s['change_pct']:.0f}%, +{format_vnd(s['diff'], compact=True)})"
            for s in spikes[:3]
        )
        render_ai_banner(
            title="Danh mục tăng mạnh so với tháng trước" if lang == "vi" else "Categories Spiking vs. Last Month",
            body_html=items_str,
            icon_name="alert_triangle",
            theme_mode=theme_mode,
        )
    else:
        render_ai_banner(
            title="Chi tiêu ổn định" if lang == "vi" else "Stable Spending Behavior",
            body_html="Không có danh mục nào tăng đột biến >20% so với tháng trước." if lang == "vi" else "No category spiked >20% compared to last month.",
            icon_name="shield_check",
            theme_mode=theme_mode,
        )

    c1, c2 = st.columns([1.05, 1.15])
    with c1:
        with st.container(border=True):
            render_section_header(
                "Phân bổ 6 danh mục chi tiêu" if lang == "vi" else "6-Category Breakdown",
                "Đặt vòng tròn bên trái & chú thích tỷ lệ bên phải (0% đè chữ)." if lang == "vi" else "Donut left + vertical percentage legend right.",
                icon_name="pie_chart",
                theme_mode=theme_mode,
            )
            if not breakdown.empty:
                st.plotly_chart(
                    build_clean_donut_figure(breakdown, spending["total_expense"], height=290, theme_mode=theme_mode, lang=lang),
                    config={"displayModeBar": False},
                )
                tbl = pd.DataFrame(
                    {
                        "Danh mục" if lang == "vi" else "Category": [cat_label(c, lang) for c in breakdown["category"]],
                        "GD" if lang == "vi" else "TX": breakdown["tx_count"].astype(int),
                        "Tổng chi" if lang == "vi" else "Total": [format_vnd(v) for v in breakdown["amount"]],
                        "%" : [f"{pct:.1f}%" for pct in breakdown["share_pct"]],
                        "MoM": [f"{chg:+.0f}%" if pd.notna(chg) else "—" for chg in breakdown["change_pct"]],
                    }
                )
                st.dataframe(tbl, hide_index=True, height=225)

    with c2:
        with st.container(border=True):
            render_section_header(
                "Xu hướng tăng giảm theo danh mục" if lang == "vi" else "Category Trend & MoM Comparison",
                "Cột đỏ đánh dấu danh mục tăng trên +20%." if lang == "vi" else "Red bars highlight categories spiking >20%.",
                icon_name="trending_up",
                theme_mode=theme_mode,
            )
            m_opt1 = "So với tháng trước" if lang == "vi" else "vs. Last Month"
            m_opt2 = "Xu hướng nhiều tháng" if lang == "vi" else "Multi-Month Trend"
            t_view = st.segmented_control("sp_trend_mode", options=[m_opt1, m_opt2], default=m_opt1, label_visibility="collapsed")

            if t_view == m_opt1 and not breakdown.empty and breakdown["prev_amount"].sum() > 0:
                xl = [cat_label(c, lang) for c in breakdown["category"]]
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(name="Tháng trước" if lang == "vi" else "Last Month", x=xl, y=breakdown["prev_amount"], marker=dict(color="#94A3B8", cornerradius=6)))
                fig_m.add_trace(
                    go.Bar(
                        name="Kỳ hiện tại" if lang == "vi" else "Current",
                        x=xl,
                        y=breakdown["amount"],
                        marker=dict(color=[p["danger"] if (pd.notna(c) and c >= 20) else p["primary"] for c in breakdown["change_pct"]], cornerradius=6),
                    )
                )
                fig_m.update_layout(barmode="group", bargap=0.25)
                apply_plotly_theme(fig_m, height=280, theme_mode=theme_mode)
                st.plotly_chart(fig_m, config={"displayModeBar": False})
            else:
                tr_df = spending["monthly_category_trend"]
                fig_l = go.Figure()
                for cat in tr_df["category"].unique():
                    sub = tr_df.loc[tr_df["category"] == cat].sort_values("year_month")
                    fig_l.add_trace(
                        go.Scatter(
                            x=sub["year_month"], y=sub["amount"], mode="lines+markers",
                            name=cat_label(cat, lang),
                            line=dict(color=get_category_color(cat), width=2.4, shape="spline"),
                        )
                    )
                apply_plotly_theme(fig_l, height=280, theme_mode=theme_mode)
                st.plotly_chart(fig_l, config={"displayModeBar": False})

            # Anomaly scatter
            cur_exp = filter_by_month(df, selected_month)
            cur_exp = cur_exp.loc[cur_exp["type"] == "expense"].copy()
            if not cur_exp.empty:
                render_section_header(
                    "Phát hiện giao dịch đột biến (IQR + Z-score)" if lang == "vi" else "Statistical Anomaly Scatter",
                    "",
                    icon_name="alert_triangle",
                    theme_mode=theme_mode,
                )
                anom_set = set(anomalies_df["description"].tolist()) if not anomalies_df.empty else set()
                cur_exp["is_anom"] = cur_exp["description"].isin(anom_set)
                fig_s = go.Figure()
                norm = cur_exp.loc[~cur_exp["is_anom"]]
                anom = cur_exp.loc[cur_exp["is_anom"]]
                fig_s.add_trace(go.Scatter(x=norm["date"], y=norm["amount"], mode="markers", name="Normal", marker=dict(color=p["primary"], size=8, opacity=0.65), text=norm["description"]))
                if not anom.empty:
                    fig_s.add_trace(go.Scatter(x=anom["date"], y=anom["amount"], mode="markers", name="Anomaly", marker=dict(color=p["danger"], size=13, line=dict(color="#FFFFFF", width=2)), text=anom["description"]))
                apply_plotly_theme(fig_s, height=195, theme_mode=theme_mode)
                st.plotly_chart(fig_s, config={"displayModeBar": False})

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        with st.container(border=True):
            render_section_header("Giao dịch bất thường phát hiện" if lang == "vi" else "Detected Anomalies", "", icon_name="alert_triangle", theme_mode=theme_mode)
            if anomalies_df.empty:
                st.success("Không phát hiện giao dịch bất thường." if lang == "vi" else "No anomalies detected.")
            else:
                for _, r in anomalies_df.iterrows():
                    render_alert_item(
                        title=str(r["description"]),
                        subtitle=f"{pd.Timestamp(r['date']).strftime('%d/%m/%Y')} · {cat_label(r['category'], lang)} · {r['reason']}",
                        amount_str=format_vnd(r["amount"]),
                        badge_text=f"{r['ratio']:.1f}x TB",
                        variant="danger",
                        theme_mode=theme_mode,
                    )

        with st.container(border=True):
            render_section_header(
                "Rò rỉ khoản chi nhỏ lặp lại (<= 100.000 ₫)" if lang == "vi" else "Micro-Spending Leaks (<= 100k VND)",
                f"{micro['count']} GD · {format_vnd(micro['total'])} ({micro['share_pct']:.1f}%)",
                icon_name="coffee",
                theme_mode=theme_mode,
            )
            hdf = micro.get("top_habits", pd.DataFrame())
            if hdf is not None and not hdf.empty:
                for _, hr in hdf.head(4).iterrows():
                    render_alert_item(
                        title=str(hr["habit_group"]),
                        subtitle=f"{int(hr['tx_count'])} GD · TB {format_vnd(hr['avg_ticket'])}",
                        amount_str=format_vnd(hr["total"]),
                        badge_text=f"{int(hr['tx_count'])}x",
                        variant="warning",
                        theme_mode=theme_mode,
                    )

    with b2:
        _render_fixed_expenses_section(user, recurring_df, theme_mode, lang)

    with st.expander("Đánh giá độ chính xác mô hình ML (Scikit-learn 5-Fold CV)" if lang == "vi" else "ML Categorization Model Accuracy (5-Fold CV)", icon=":material/neurology:"):
        ev = get_ml_evaluation()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Logistic Regression CV", f"{ev['accuracy_pct']}%")
        m2.metric("Macro F1-Score", f"{ev['macro_f1_pct']}%")
        m3.metric("Random Forest CV", f"{ev['rf_comparison_accuracy_pct']}%")
        m4.metric("Training Corpus", f"{ev['corpus_size']} samples")
        per_df = pd.DataFrame(ev["per_class"])
        per_df["category"] = per_df["category"].map(lambda c: cat_label(c, lang))
        st.dataframe(per_df, hide_index=True)
