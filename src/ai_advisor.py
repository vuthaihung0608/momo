"""LLM AI Advisor Integration & Data-Grounded Financial Q&A (Member 3 — Backend & Integration).

Integrates Google Gemini API (`google-genai`) with strict Python/Pandas data grounding:
1. Extracts verified VND metrics, category breakdown, spikes, anomalies, recurring bills,
   micro-spending leaks, and 30-day cashflow forecast directly from the user's live DataFrame.
2. Automatically computes What-If purchase simulations when the user mentions an amount
   (e.g. "Nếu tháng sau tôi mua laptop 15 triệu thì sao?").
3. Passes the verified JSON facts into Gemini (`gemini-2.5-flash`) when `GEMINI_API_KEY` is
   configured (via `.env`, environment variable, or sidebar input), or seamlessly falls back
   to the deterministic Data-Grounded Analytics Engine offline — ALWAYS paired with matching
   interactive Plotly visualizations.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

from src.analysis import CATEGORY_VI_NAMES, analyze_spending
from src.forecasting import forecast_cashflow
from src.llm_client import generate_universal_reply

load_dotenv()

PRO_COLORS = {
    "primary": "#1E40AF",
    "primary_light": "#2563EB",
    "success": "#059669",
    "danger": "#DC2626",
    "warning": "#D97706",
    "ink": "#0F172A",
    "muted": "#475569",
    "border": "#E2E8F0",
}

CAT_COLORS = {
    "Food": "#EA580C",
    "Shopping": "#7C3AED",
    "Transport": "#0284C7",
    "Bills": "#1E40AF",
    "Entertainment": "#DB2777",
    "Other": "#475569",
    "Income": "#059669",
}


def _fmt_vnd(amount: float, show_sign: bool = False, compact: bool = False) -> str:
    sign = ""
    if show_sign:
        sign = "+" if amount > 0 else ("-" if amount < 0 else "")
    elif amount < 0:
        sign = "-"
    abs_val = abs(float(amount))
    if compact:
        if abs_val >= 1_000_000:
            return f"{sign}{abs_val / 1_000_000:.2f} tr ₫"
        if abs_val >= 1_000:
            return f"{sign}{abs_val / 1_000:.0f}k ₫"
    return f"{sign}{int(round(abs_val)):,} ₫".replace(",", ".")


def _cat_vi(cat: str) -> str:
    return CATEGORY_VI_NAMES.get(cat, cat)


def _style_mini_fig(fig: go.Figure, height: int = 260, show_legend: bool = False) -> go.Figure:
    fig.update_layout(
        font=dict(family="IBM Plex Sans, Inter, sans-serif", color=PRO_COLORS["ink"], size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=14, r=48, t=20, b=16),
        showlegend=show_legend,
        hoverlabel=dict(bgcolor="#0F172A", font_color="#FFFFFF", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor=PRO_COLORS["border"], tickfont=dict(color=PRO_COLORS["muted"], size=11))
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(color=PRO_COLORS["muted"], size=11))
    return fig


def extract_vnd_amount(question: str) -> float | None:
    """Extract Vietnamese currency amounts like '15 triệu', '2.5tr', '500k', '15000000'."""
    q = question.lower().replace(",", ".")
    m_tr = re.search(r"(\d+(?:\.\d+)?)\s*(?:triệu|trieu|tr)\b", q)
    if m_tr:
        return float(m_tr.group(1)) * 1_000_000
    m_k = re.search(r"(\d+(?:\.\d+)?)\s*(?:nghìn|nghin|ngàn|k)\b", q)
    if m_k:
        return float(m_k.group(1)) * 1_000
    m_raw = re.search(r"\b(\d{6,10})\b", q)
    if m_raw:
        return float(m_raw.group(1))
    return None


def _build_category_chart(breakdown: pd.DataFrame) -> go.Figure | None:
    if breakdown.empty:
        return None
    top = breakdown.head(6).iloc[::-1]
    labels = [_cat_vi(c) for c in top["category"]]
    colors = [CAT_COLORS.get(c, "#475569") for c in top["category"]]
    fig = go.Figure(
        go.Bar(
            x=top["amount"],
            y=labels,
            orientation="h",
            marker=dict(color=colors, cornerradius=6),
            text=[_fmt_vnd(v, compact=True) for v in top["amount"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Chi tiêu: %{x:,.0f} ₫<extra></extra>",
        )
    )
    _style_mini_fig(fig, height=250, show_legend=False)
    fig.update_layout(margin=dict(l=12, r=70, t=12, b=12))
    return fig


def _build_whatif_chart(current_bal: float, proj_before: float, proj_after: float) -> go.Figure:
    labels = ["Số dư hiện tại", "Dự báo 30 ngày (Không mua)", "Dự báo 30 ngày (Nếu mua)"]
    values = [current_bal, proj_before, proj_after]
    colors = [
        PRO_COLORS["primary"],
        PRO_COLORS["success"] if proj_before >= 0 else PRO_COLORS["danger"],
        PRO_COLORS["success"] if proj_after >= 0 else PRO_COLORS["danger"],
    ]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker=dict(color=colors, cornerradius=8),
            text=[_fmt_vnd(v, compact=True) for v in values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{y:,.0f} ₫<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color=PRO_COLORS["danger"], line_width=1.4)
    _style_mini_fig(fig, height=265, show_legend=False)
    fig.update_layout(margin=dict(l=16, r=16, t=28, b=14))
    return fig


def _build_mom_chart(breakdown: pd.DataFrame) -> go.Figure | None:
    if breakdown.empty or breakdown["prev_amount"].sum() <= 0:
        return None
    sub = breakdown.head(6)
    labels = [_cat_vi(c) for c in sub["category"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Tháng trước", x=labels, y=sub["prev_amount"], marker=dict(color="#CBD5E1", cornerradius=6)))
    fig.add_trace(
        go.Bar(
            name="Kỳ hiện tại",
            x=labels,
            y=sub["amount"],
            marker=dict(
                color=[PRO_COLORS["danger"] if (pd.notna(c) and c >= 20) else PRO_COLORS["primary"] for c in sub["change_pct"]],
                cornerradius=6,
            ),
        )
    )
    fig.update_layout(barmode="group")
    _style_mini_fig(fig, height=260, show_legend=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def _build_recurring_chart(recurring_df: pd.DataFrame) -> go.Figure | None:
    if recurring_df.empty:
        return None
    fig = go.Figure(
        go.Bar(
            x=recurring_df["avg_amount"][::-1],
            y=recurring_df["merchant"][::-1],
            orientation="h",
            marker=dict(color=PRO_COLORS["primary_light"], cornerradius=6),
            text=[_fmt_vnd(v, compact=True) for v in recurring_df["avg_amount"][::-1]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:,.0f} ₫/tháng<extra></extra>",
        )
    )
    _style_mini_fig(fig, height=255, show_legend=False)
    fig.update_layout(margin=dict(l=12, r=70, t=12, b=12))
    return fig


def _choose_chart_and_facts(
    question: str,
    df: pd.DataFrame,
    selected_month: str,
    monthly_budget: float,
    fixed_expenses: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], go.Figure | None, str]:
    """Compute verified financial facts and select a relevant inline chart only for personal-data queries."""
    q = question.lower().strip()
    if df is None or df.empty:
        fixed_list = list(fixed_expenses or [])
        fixed_total = sum(float(x.get("amount") or 0) for x in fixed_list)
        empty_facts = {
            "has_transactions": False,
            "period": "Chưa có giao dịch",
            "income_vnd": 0,
            "expense_vnd": 0,
            "net_balance_vnd": 0,
            "cumulative_balance_vnd": 0,
            "savings_rate_pct": 0.0,
            "monthly_budget_vnd": round(monthly_budget),
            "tx_count": 0,
            "recurring_monthly_total_vnd": round(fixed_total),
            "recurring_items": [
                {"merchant": str(x.get("name", "")), "category": _cat_vi(str(x.get("category", "Bills"))), "monthly_vnd": round(float(x.get("amount") or 0))}
                for x in fixed_list
            ],
            "whatif_simulation": None,
            "_spending_raw": None,
            "_forecast_raw": None,
        }
        return empty_facts, None, "general"

    cur_df = df.copy() if selected_month == "ALL" else df.loc[df["year_month"] == selected_month].copy()
    income = float(cur_df.loc[cur_df["type"] == "income", "amount"].sum())
    expense = float(cur_df.loc[cur_df["type"] == "expense", "amount"].sum())
    net_balance = income - expense
    up_to = df if selected_month == "ALL" else df.loc[df["year_month"] <= selected_month]
    cumulative_balance = float(up_to["signed_amount"].sum())

    spending = analyze_spending(df, selected_month, fixed_expenses=fixed_expenses)
    forecast = forecast_cashflow(df, monthly_budget=monthly_budget, fixed_expenses=fixed_expenses)
    breakdown = spending["category_breakdown"]
    recurring_df = spending["recurring"]
    anomalies_df = spending["anomalies"]
    micro = spending.get("micro_spending", {})

    cost = extract_vnd_amount(q)
    intent = "general"
    chart: go.Figure | None = None
    whatif_data = None

    if cost is not None and any(k in q for k in ["mua", "nếu", "laptop", "điện thoại", "xe", "iphone", "macbook", "chi thêm", "tốn", "trả góp", "buy", "what if"]):
        intent = "whatif"
        proj_before = forecast["balance_30d_base"]
        proj_after = proj_before - cost
        monthly_inc = float(df.loc[df["type"] == "income"].groupby("year_month")["amount"].sum().mean()) if not df.loc[df["type"] == "income"].empty else 0.0
        monthly_exp = float(df.loc[df["type"] == "expense"].groupby("year_month")["amount"].sum().mean()) if not df.loc[df["type"] == "expense"].empty else 0.0
        avg_saving = max(monthly_inc - monthly_exp, 0.0)
        months_needed = int(np.ceil(cost / avg_saving)) if avg_saving > 100_000 else 12
        whatif_data = {
            "purchase_cost": cost,
            "current_balance": forecast["current_balance"],
            "projected_30d_before": proj_before,
            "projected_30d_after": proj_after,
            "deficit": abs(proj_after) if proj_after < 0 else 0.0,
            "avg_monthly_saving": avg_saving,
            "months_to_save": months_needed,
            "installment_6m": cost / 6.0,
        }
        chart = _build_whatif_chart(forecast["current_balance"], proj_before, proj_after)
    elif any(k in q for k in ["nhiều nhất", "top", "vào đâu", "danh mục nào nhiều", "tiêu gì", "chi nhiều", "spend the most"]):
        intent = "top_category"
        chart = _build_category_chart(breakdown)
    elif any(k in q for k in ["định kỳ", "cố định", "subscription", "spotify", "netflix", "tự động", "quên", "đăng ký", "recurring"]):
        intent = "recurring"
        chart = _build_recurring_chart(recurring_df)
    elif any(k in q for k in ["bất thường", "tăng", "đột biến", "thất thoát", "lạ", "vọt", "spiking", "anomal"]):
        intent = "anomaly"
        chart = _build_mom_chart(breakdown) or _build_category_chart(breakdown)
    elif any(k in q for k in ["tiết kiệm", "cắt giảm", "giảm chi", "ngân sách", "save an extra", "budget"]):
        intent = "savings"
        chart = _build_category_chart(breakdown)
    elif any(k in q for k in ["sức khỏe tài chính", "tóm tắt", "tổng quan", "số dư của tôi", "chi tiêu của tôi", "financial health", "summarize my"]):
        intent = "summary"
        chart = _build_category_chart(breakdown)

    facts = {
        "period": f"Tháng {selected_month}" if selected_month != "ALL" else "Toàn bộ kỳ dữ liệu",
        "income_vnd": round(income),
        "expense_vnd": round(expense),
        "net_balance_vnd": round(net_balance),
        "cumulative_balance_vnd": round(cumulative_balance),
        "savings_rate_pct": round((net_balance / income * 100.0) if income > 0 else 0.0, 1),
        "monthly_budget_vnd": round(monthly_budget),
        "tx_count": int(len(cur_df)),
        "top_category": _cat_vi(spending["top_category"]),
        "top_category_amount_vnd": round(spending["top_category_amount"]),
        "top_category_share_pct": round(spending["top_category_share"], 1),
        "categories": [
            {
                "category": _cat_vi(r["category"]),
                "amount_vnd": round(float(r["amount"])),
                "share_pct": round(float(r["share_pct"]), 1),
                "tx_count": int(r["tx_count"]),
                "mom_change_pct": round(float(r["change_pct"]), 1) if pd.notna(r["change_pct"]) else None,
            }
            for _, r in breakdown.iterrows()
        ],
        "spikes": [
            {
                "category": _cat_vi(s["category"]),
                "change_pct": round(s["change_pct"], 1),
                "diff_vnd": round(s["diff"]),
            }
            for s in spending["spikes"]
        ],
        "anomalies": [
            {
                "description": str(a["description"]),
                "date": pd.Timestamp(a["date"]).strftime("%d/%m/%Y"),
                "amount_vnd": round(float(a["amount"])),
                "ratio_vs_avg": float(a["ratio"]),
            }
            for _, a in anomalies_df.head(5).iterrows()
        ],
        "recurring_monthly_total_vnd": round(spending["recurring_monthly_total"]),
        "recurring_items": [
            {
                "merchant": str(r["merchant"]),
                "category": _cat_vi(r["category"]),
                "monthly_vnd": round(float(r["avg_amount"])),
                "annual_vnd": round(float(r["annual_cost"])),
                "next_due": pd.Timestamp(r["next_due_date"]).strftime("%d/%m/%Y"),
            }
            for _, r in recurring_df.iterrows()
        ],
        "micro_spending": {
            "count": int(micro.get("count", 0)),
            "total_vnd": round(float(micro.get("total", 0.0))),
            "share_pct": round(float(micro.get("share_pct", 0.0)), 1),
        },
        "forecast": {
            "model": forecast.get("model_name", "Statsmodels SES"),
            "eom_balance_vnd": round(forecast["eom_scenario_balance"]),
            "next_month_expense_vnd": round(forecast["next_month_expense_scen"]),
            "overrun_risk_pct": int(forecast["overrun_risk"]),
            "status": forecast["status_label"],
            "balance_30d_vnd": round(forecast["balance_30d_base"]),
        },
        "whatif_simulation": whatif_data,
        "_spending_raw": spending,
        "_forecast_raw": forecast,
    }
    return facts, chart, intent


def _call_gemini_llm(
    question: str,
    facts: dict[str, Any],
    api_key: str,
    history: list[dict[str, Any]] | None = None,
    lang: str = "vi",
) -> tuple[str | None, str]:
    """Call universal LLM (Gemini / OpenAI / Groq / Live AI) capable of answering ANY question."""
    serializable_facts = {k: v for k, v in facts.items() if not k.startswith("_")}
    lang_rule = (
        "Trả lời cùng ngôn ngữ với câu hỏi của người dùng (mặc định Tiếng Việt tự nhiên, rõ ràng, định dạng Markdown đẹp)."
        if lang == "vi"
        else "Respond in the same language as the user's question (default clear Markdown English)."
    )
    system_instruction = (
        "Bạn là MoneyLens AI Advisor — một trợ lý AI thông minh toàn năng (tương tự ChatGPT / Gemini) tích hợp trong ứng dụng quản lý tài chính cá nhân MoneyLens AI.\n"
        "KHẢ NĂNG & QUY TẮC:\n"
        "1. Bạn có thể trả lời MỌI câu hỏi thuộc MỌI lĩnh vực (tài chính, đầu tư, học tập, lập trình, đời sống, viết lách, tính toán, kiến thức tổng hợp...) một cách chính xác, chi tiết, hữu ích và tự nhiên — KHÔNG từ chối câu hỏi ngoài tài chính.\n"
        "2. Khi câu hỏi liên quan đến chi tiêu, số dư, ngân sách hoặc giao dịch cá nhân của người dùng, hãy sử dụng CHÍNH XÁC số liệu thực tế trong ngữ cảnh tài chính đính kèm bên dưới (tuyệt đối không bịa số, định dạng tiền kiểu 10.500.000 ₫). Nếu người dùng chưa có giao dịch nào (`tx_count == 0`), hãy nói rõ và vẫn trả lời trọn vẹn câu hỏi.\n"
        f"3. {lang_rule}\n"
        "4. Không nhắc tới chữ 'JSON' hay chi tiết kỹ thuật nội bộ.\n\n"
        f"[Ngữ cảnh tài chính cá nhân hiện tại của người dùng]:\n{json.dumps(serializable_facts, ensure_ascii=False)}"
    )
    return generate_universal_reply(
        user_message=question,
        system_instruction=system_instruction,
        history=history,
        api_key=api_key,
        max_tokens=1000,
        temperature=0.55,
    )


def _build_offline_grounded_answer(
    question: str,
    df: pd.DataFrame,
    selected_month: str,
    facts: dict[str, Any],
    intent: str,
) -> str:
    """Deterministic data-grounded Vietnamese financial response when Gemini API key is absent/offline."""
    period_text = facts["period"]
    spending = facts.get("_spending_raw")
    if spending is None:
        return (
            "Hiện kết nối tới mô hình AI trực tuyến đang tạm gián đoạn và bạn cũng chưa có giao dịch nào trong tài khoản. "
            "Hãy kiểm tra mạng hoặc dán khóa **Gemini / OpenAI / Groq API Key** trong mục **Cài đặt AI** bên trái để trò chuyện tự do mọi chủ đề!"
        )
    breakdown = spending["category_breakdown"]
    recurring_df = spending["recurring"]
    anomalies_df = spending["anomalies"]

    if intent == "whatif" and facts["whatif_simulation"]:
        w = facts["whatif_simulation"]
        cost = w["purchase_cost"]
        if w["projected_30d_after"] < 0:
            return (
                f"### Phân tích kịch bản mua sắm **{_fmt_vnd(cost)}**\n\n"
                f"Dựa trên số liệu thực tế của bạn:\n"
                f"- **Số dư tích lũy hiện tại:** `{_fmt_vnd(w['current_balance'])}`\n"
                f"- **Dự báo số dư 30 ngày tới (không mua):** `{_fmt_vnd(w['projected_30d_before'])}`\n"
                f"- **Dự báo nếu chi ngay {_fmt_vnd(cost)}:** **`{_fmt_vnd(w['projected_30d_after'])}`** *(thâm hụt **{_fmt_vnd(w['deficit'])}**)*\n\n"
                f"#### Khuyến nghị từ MoneyLens AI:\n"
                f"1. **Không nên thanh toán 1 lần ngay tháng sau** vì dòng tiền sẽ bị âm.\n"
                f"2. Với tốc độ tiết kiệm trung bình khoảng **{_fmt_vnd(w['avg_monthly_saving'])}/tháng**, bạn nên tích lũy thêm khoảng **{w['months_to_save']} tháng** (hoặc cắt 25% Mua sắm & Ăn uống để rút ngắn còn **{max(w['months_to_save'] - 2, 1)} tháng**).\n"
                f"3. Nếu cần mua sớm phục vụ học tập/công việc, cân nhắc **trả góp 0% trong 6 tháng** (~**{_fmt_vnd(w['installment_6m'])}/tháng**) để giữ số dư luôn dương."
            )
        return (
            f"### Bạn hoàn toàn có thể chi trả khoản **{_fmt_vnd(cost)}**\n\n"
            f"- **Số dư hiện tại:** `{_fmt_vnd(w['current_balance'])}`\n"
            f"- **Dự báo 30 ngày tới (trước khi mua):** `{_fmt_vnd(w['projected_30d_before'])}`\n"
            f"- **Dự báo 30 ngày tới (sau khi mua):** **`{_fmt_vnd(w['projected_30d_after'])}`** *(vẫn dương an toàn)*.\n\n"
            f"Gợi ý: Hãy giữ lại quỹ dự phòng tối thiểu bằng 1 tháng chi phí cố định (**{_fmt_vnd(facts['recurring_monthly_total_vnd'])}**)."
        )

    if intent == "top_category" and not breakdown.empty:
        top1 = breakdown.iloc[0]
        top2 = breakdown.iloc[1] if len(breakdown) > 1 else None
        cur_exp = df.loc[df["type"] == "expense"]
        if selected_month != "ALL":
            cur_exp = cur_exp.loc[cur_exp["year_month"] == selected_month]
        top_tx = cur_exp.loc[cur_exp["category"] == top1["category"]].sort_values("amount", ascending=False).head(3)
        merchants_md = "\n".join(
            f"  - `{r['description']}` ({pd.Timestamp(r['date']).strftime('%d/%m')}): **{_fmt_vnd(r['amount'])}**"
            for _, r in top_tx.iterrows()
        )
        second = (
            f"\n- Xếp thứ 2 là **{_cat_vi(top2['category'])}** với **{_fmt_vnd(top2['amount'])}** ({top2['share_pct']:.1f}%)."
            if top2 is not None
            else ""
        )
        return (
            f"### Danh mục bạn chi nhiều nhất ({period_text})\n\n"
            f"- Bạn chi nhiều nhất vào **{_cat_vi(top1['category'])}** với tổng **{_fmt_vnd(top1['amount'])}**, "
            f"chiếm **{top1['share_pct']:.1f}%** tổng chi tiêu ({int(top1['tx_count'])} giao dịch).{second}\n\n"
            f"**Các khoản chi lớn nhất trong nhóm {_cat_vi(top1['category'])}:**\n{merchants_md}\n\n"
            f"**Gợi ý hành động:** Nếu đặt mục tiêu giảm 15% cho nhóm này ở kỳ tới, bạn sẽ tiết kiệm thêm **{_fmt_vnd(float(top1['amount']) * 0.15)}**."
        )

    if intent == "recurring":
        if recurring_df.empty:
            return "Chưa phát hiện khoản chi định kỳ lặp lại qua từ 2 tháng trở lên trong dữ liệu hiện tại."
        items_md = "\n".join(
            f"- **{r['merchant']}** ({_cat_vi(r['category'])}): **{_fmt_vnd(r['avg_amount'])}/tháng** "
            f"*(~{_fmt_vnd(r['annual_cost'])}/năm · kỳ tới dự kiến {pd.Timestamp(r['next_due_date']).strftime('%d/%m')})*"
            for _, r in recurring_df.iterrows()
        )
        subs = recurring_df.loc[recurring_df["category"] == "Entertainment"]
        sub_note = ""
        if not subs.empty:
            sub_note = (
                f"\n\n**Lưu ý gói đăng ký (Subscriptions):** Riêng {', '.join(subs['merchant'].tolist())} đang tiêu tốn "
                f"**{_fmt_vnd(float(subs['avg_amount'].sum()))}/tháng** (~**{_fmt_vnd(float(subs['annual_cost'].sum()))}/năm**). "
                "Hãy rà soát xem gói nào ít dùng hoặc chuyển sang gói Student/Family."
            )
        return (
            f"### Các khoản chi định kỳ MoneyLens phát hiện\n\n"
            f"Tổng chi phí cố định & định kỳ mỗi tháng là **{_fmt_vnd(facts['recurring_monthly_total_vnd'])}** "
            f"(**{_fmt_vnd(facts['recurring_monthly_total_vnd'] * 12)}/năm**):\n\n{items_md}{sub_note}"
        )

    if intent == "anomaly":
        spike_md = "\n".join(
            f"- **{_cat_vi(s['category'])}**: tăng **+{s['change_pct']:.1f}%** (tăng thêm **{_fmt_vnd(s['diff'])}** so với tháng trước)."
            for s in spending["spikes"]
        ) or "- Không có danh mục nào tăng đột biến trên 20%."
        anom_md = "\n".join(
            f"- `{a['description']}` ({pd.Timestamp(a['date']).strftime('%d/%m')}): **{_fmt_vnd(a['amount'])}** — *{a['reason']}*."
            for _, a in anomalies_df.head(4).iterrows()
        ) or "- Chưa ghi nhận giao dịch đột biến bất thường."
        micro = facts["micro_spending"]
        return (
            f"### Cảnh báo tăng chi tiêu & giao dịch bất thường ({period_text})\n\n"
            f"**Danh mục tăng mạnh so với tháng trước:**\n{spike_md}\n\n"
            f"**Giao dịch bất thường nổi bật:**\n{anom_md}\n\n"
            f"**Rò rỉ khoản chi nhỏ lặp lại (<= 100k):** Có **{micro['count']} giao dịch nhỏ** cộng dồn thành **{_fmt_vnd(micro['total_vnd'])}** ({micro['share_pct']}% tổng chi)."
        )

    if intent == "savings":
        target = extract_vnd_amount(question) or 2_000_000
        disc = breakdown.loc[breakdown["category"].isin(["Shopping", "Food", "Entertainment"])].copy()
        disc_total = float(disc["amount"].sum()) if not disc.empty else 1.0
        lines = []
        for _, r in disc.iterrows():
            cut = min(float(r["amount"]) * 0.35, target * (float(r["amount"]) / disc_total))
            pct = (cut / float(r["amount"]) * 100.0) if float(r["amount"]) > 0 else 0.0
            lines.append(
                f"- **{_cat_vi(r['category'])}**: giảm khoảng **{pct:.0f}%** (~**{_fmt_vnd(cut)}/tháng**) từ mức {_fmt_vnd(r['amount'])}."
            )
        plan_md = "\n".join(lines) if lines else "- Cắt giảm 15% tốc độ chi biến đổi hàng ngày."
        return (
            f"### Kế hoạch tiết kiệm thêm **{_fmt_vnd(target)}/tháng**\n\n"
            f"Tổng chi linh hoạt (Mua sắm, Ăn uống, Giải trí) trong {period_text} là **{_fmt_vnd(disc_total)}**. Đề xuất phân bổ cắt giảm:\n\n"
            f"{plan_md}\n\n"
            "Mẹo: Bạn có thể vào trang **03 · Dự báo tài chính** để kéo thử thanh trượt cắt giảm từng nhóm và xem số dư cuối tháng tăng lên ngay lập tức."
        )

    fc = facts["forecast"]
    return (
        f"### Tóm tắt sức khỏe tài chính ({period_text})\n\n"
        f"- **Tổng thu nhập:** `{_fmt_vnd(facts['income_vnd'])}`\n"
        f"- **Tổng chi tiêu:** `{_fmt_vnd(facts['expense_vnd'])}` ({facts['tx_count']} giao dịch)\n"
        f"- **Dòng tiền ròng kỳ này:** **`{_fmt_vnd(facts['net_balance_vnd'], show_sign=True)}`** *(tỷ lệ tiết kiệm: {facts['savings_rate_pct']}%)*\n"
        f"- **Danh mục chi lớn nhất:** **{facts['top_category']}** ({_fmt_vnd(facts['top_category_amount_vnd'])} · {facts['top_category_share_pct']}%)\n"
        f"- **Dự báo số dư cuối tháng ({fc['model']}):** `{_fmt_vnd(fc['eom_balance_vnd'])}` (*{fc['status']}*)\n\n"
        "Bạn có thể hỏi cụ thể hơn, ví dụ: *\"Tôi tiêu nhiều nhất vào đâu?\"* hoặc *\"Nếu tháng sau tôi mua laptop 15 triệu thì sao?\"*."
    )


def ask_advisor(
    question: str,
    df: pd.DataFrame,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Answer ANY question via Universal LLM (Gemini / OpenAI / Groq / Live AI) grounded in live user data."""
    ctx = context or {}
    selected_month = str(ctx.get("selected_month", "ALL"))
    monthly_budget = float(ctx.get("monthly_budget", 8_000_000))
    api_key = str(ctx.get("api_key") or os.getenv("GEMINI_API_KEY") or "").strip()
    history = ctx.get("history")
    lang = str(ctx.get("lang", "vi"))
    fixed_expenses = ctx.get("fixed_expenses")

    facts, chart, intent = _choose_chart_and_facts(
        question, df, selected_month, monthly_budget, fixed_expenses=fixed_expenses
    )

    llm_answer, llm_source = _call_gemini_llm(question, facts, api_key, history=history, lang=lang)
    if llm_answer:
        return {
            "answer": llm_answer,
            "chart": chart,
            "source": f"{llm_source} · MoneyLens AI",
        }

    if llm_source == "RATE_LIMIT_402" and intent == "general":
        return {
            "answer": (
                "Cổng AI miễn phí không cần khóa vừa chạm giới hạn tần suất (1 câu / 45 giây). "
                "Bạn có thể đợi ~30 giây rồi hỏi lại, **hoặc** dán **Gemini API Key miễn phí** (`aistudio.google.com/apikey`) / **Groq / OpenAI API Key** vào mục **AI API Key** ở góc dưới bên trái để chat mọi câu hỏi liên tục không giới hạn!"
                if lang == "vi"
                else "The zero-key public AI endpoint hit its brief rate limit (1 reply / 45s). Wait ~30s and retry, or paste a free **Gemini / Groq / OpenAI API Key** under **AI API Key** on the bottom-left for unlimited fast replies!"
            ),
            "chart": None,
            "source": "MoneyLens AI · Rate Limit Notice",
        }

    offline_answer = _build_offline_grounded_answer(question, df, selected_month, facts, intent)
    return {
        "answer": offline_answer,
        "chart": chart,
        "source": "MoneyLens Offline Grounded Engine",
    }
