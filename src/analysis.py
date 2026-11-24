"""Spending Pattern, Anomaly, Recurring & Micro-Spending Analysis Engine (Member 2 — Data & AI).

Implements:
- 6-category spending breakdown & Month-over-Month spike detection
- Statistical Anomaly Detection (IQR + Z-score hybrid excluding fixed recurring bills)
- Rule-based Recurring & Subscription Detection (with annual burn & next expected charge date)
- Micro-Spending ("Latte Factor") Leak Detector for small repeating expenses <= 100,000 VND
"""

from __future__ import annotations

import calendar
import re
from typing import Any

import numpy as np
import pandas as pd

CATEGORY_VI_NAMES = {
    "Food": "Ăn uống",
    "Shopping": "Mua sắm",
    "Transport": "Di chuyển",
    "Bills": "Hóa đơn",
    "Entertainment": "Giải trí",
    "Other": "Khác",
    "Income": "Thu nhập",
}


def normalize_merchant_key(description: str) -> str:
    """Create canonical merchant key for recurring and habit grouping."""
    text = str(description).lower().strip()
    text = re.sub(r"tháng\s*\d+", "", text)
    text = re.sub(r"\b\d{1,2}[./-]\d{1,2}\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_previous_month(df: pd.DataFrame, selected_month: str) -> str | None:
    """Return the immediately preceding YYYY-MM month before selected_month."""
    months = sorted(df["year_month"].dropna().unique().tolist())
    if selected_month not in months:
        return None
    idx = months.index(selected_month)
    return months[idx - 1] if idx > 0 else None


def _next_due_from_day(latest_date: pd.Timestamp, due_day: int) -> pd.Timestamp:
    """Next calendar occurrence of `due_day` strictly after `latest_date`."""
    year, month = latest_date.year, latest_date.month
    cand_day = min(max(int(due_day), 1), calendar.monthrange(year, month)[1])
    candidate = pd.Timestamp(year=year, month=month, day=cand_day)
    if candidate <= latest_date:
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        cand_day = min(max(int(due_day), 1), calendar.monthrange(next_year, next_month)[1])
        candidate = pd.Timestamp(year=next_year, month=next_month, day=cand_day)
    return candidate


def detect_recurring_transactions(df: pd.DataFrame, fixed_expenses: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    """Rule-based detection of monthly recurring obligations & subscriptions across >= 2 months.

    `fixed_expenses` are user-defined fixed monthly items (added manually in the UI); they are always
    included and override any auto-detected item with the same merchant name.
    """
    cols = [
        "merchant", "category", "avg_amount", "months_count", "typical_day",
        "annual_cost", "next_due_date", "is_manual", "fixed_id",
    ]
    exp = df.loc[df["type"] == "expense"].copy()
    manual_items = list(fixed_expenses or [])
    if exp.empty and not manual_items:
        return pd.DataFrame(columns=cols)

    exp["merchant_key"] = exp["description"].map(normalize_merchant_key)
    latest_date = pd.Timestamp(df["date"].max()) if not df.empty else pd.Timestamp.today().normalize()
    total_months_in_data = max(int(df["year_month"].nunique()), 1)
    min_required_months = max(2, int(np.ceil(total_months_in_data * 0.6)))
    recurring_hint_kws = (
        "thuê", "điện", "nước", "internet", "4g", "5g", "wifi", "spotify", "netflix",
        "icloud", "youtube", "gym", "bảo hiểm", "gói", "subscription", "premium", "membership",
        "vé xe buýt tháng", "gửi xe tháng",
    )

    records = []
    for key, grp in exp.groupby("merchant_key"):
        unique_months = int(grp["year_month"].nunique())
        if unique_months < min_required_months:
            continue
        tx_per_month = len(grp) / unique_months
        if tx_per_month > 1.6:
            continue

        mean_amt = float(grp["amount"].mean())
        std_amt = float(grp["amount"].std(ddof=0)) if len(grp) > 1 else 0.0
        cv = (std_amt / mean_amt) if mean_amt > 0 else 1.0
        if cv > 0.22:
            continue

        display_name = str(grp.sort_values("date").iloc[-1]["description"])
        category = str(grp["category"].mode().iloc[0])
        has_hint = any(kw in key for kw in recurring_hint_kws)
        day_std = float(grp["date"].dt.day.std(ddof=0)) if len(grp) > 1 else 0.0

        # Avoid flagging casual food/coffee/ride-hailing/haircuts as fixed monthly bills
        if category in {"Food", "Transport", "Other"} and not has_hint:
            continue
        if category not in {"Bills", "Entertainment"} and not has_hint and day_std > 3.0:
            continue

        typical_day = int(round(float(grp["date"].dt.day.median())))
        year, month = latest_date.year, latest_date.month
        cand_day = min(typical_day, calendar.monthrange(year, month)[1])
        candidate = pd.Timestamp(year=year, month=month, day=cand_day)
        if candidate <= latest_date:
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            cand_day = min(typical_day, calendar.monthrange(next_year, next_month)[1])
            candidate = pd.Timestamp(year=next_year, month=next_month, day=cand_day)

        records.append(
            {
                "merchant": display_name,
                "category": category,
                "avg_amount": round(mean_amt),
                "months_count": unique_months,
                "typical_day": typical_day,
                "annual_cost": round(mean_amt * 12),
                "next_due_date": candidate,
                "is_manual": False,
                "fixed_id": None,
            }
        )

    if manual_items:
        manual_keys = {normalize_merchant_key(it.get("name", "")) for it in manual_items}
        records = [r for r in records if normalize_merchant_key(r["merchant"]) not in manual_keys]
        for it in manual_items:
            amt = float(it.get("amount") or 0)
            if amt <= 0:
                continue
            due_day = int(it.get("due_day") or 1)
            records.append(
                {
                    "merchant": str(it.get("name", "")).strip() or "Khoản cố định",
                    "category": str(it.get("category") or "Bills"),
                    "avg_amount": round(amt),
                    "months_count": 0,
                    "typical_day": due_day,
                    "annual_cost": round(amt * 12),
                    "next_due_date": _next_due_from_day(latest_date, due_day),
                    "is_manual": True,
                    "fixed_id": it.get("id"),
                }
            )

    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records).sort_values("avg_amount", ascending=False).reset_index(drop=True)


def detect_anomalies(df: pd.DataFrame, selected_month: str) -> pd.DataFrame:
    """Statistical IQR + Z-score anomaly detection per category (excluding fixed recurring bills)."""
    cols = ["date", "description", "category", "amount", "cat_avg", "ratio", "z_score", "reason"]
    exp_all = df.loc[df["type"] == "expense"].copy()
    cur_exp = exp_all.copy() if selected_month == "ALL" else exp_all.loc[exp_all["year_month"] == selected_month].copy()
    if cur_exp.empty:
        return pd.DataFrame(columns=cols)

    recurring_df = detect_recurring_transactions(df)
    recurring_keys = set(recurring_df["merchant"].map(normalize_merchant_key)) if not recurring_df.empty else set()

    anomalies = []
    for idx, row in cur_exp.iterrows():
        m_key = normalize_merchant_key(row["description"])
        if m_key in recurring_keys:
            continue

        cat = str(row["category"])
        peers = exp_all.loc[(exp_all["category"] == cat) & (exp_all.index != idx), "amount"]
        if len(peers) < 3:
            non_rec_mask = ~exp_all["description"].map(normalize_merchant_key).isin(recurring_keys)
            peers = exp_all.loc[non_rec_mask & (exp_all.index != idx), "amount"]
        if peers.empty:
            continue

        mean_val = float(peers.mean())
        std_val = float(peers.std(ddof=0))
        median_val = float(peers.median())
        q75 = float(peers.quantile(0.75))
        q25 = float(peers.quantile(0.25))
        iqr_fence = q75 + 1.8 * max(q75 - q25, median_val * 0.25)
        z_threshold = mean_val + 2.0 * std_val

        amt = float(row["amount"])
        ratio = amt / max(mean_val, 1.0)
        z_score = (amt - mean_val) / max(std_val, 1.0)

        if (amt > max(iqr_fence, z_threshold) and ratio >= 2.2) or (amt >= 1_500_000 and ratio >= 2.5):
            vi_cat = CATEGORY_VI_NAMES.get(cat, cat)
            anomalies.append(
                {
                    "date": row["date"],
                    "description": row["description"],
                    "category": cat,
                    "amount": amt,
                    "cat_avg": round(mean_val),
                    "ratio": round(ratio, 1),
                    "z_score": round(z_score, 2),
                    "reason": f"Cao gấp {ratio:.1f}x mức trung bình nhóm {vi_cat} (Z={z_score:.1f})",
                }
            )

    if not anomalies:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(anomalies).sort_values("amount", ascending=False).reset_index(drop=True)


def detect_micro_spending(df: pd.DataFrame, selected_month: str, threshold: float = 100_000) -> dict[str, Any]:
    """Identify small repeating expenses (<= 100,000 VND) that quietly drain monthly cash ('Latte Factor')."""
    exp = df.loc[df["type"] == "expense"].copy()
    cur_exp = exp.copy() if selected_month == "ALL" else exp.loc[exp["year_month"] == selected_month].copy()
    total_exp = float(cur_exp["amount"].sum())

    micro = cur_exp.loc[cur_exp["amount"] <= threshold].copy()
    if micro.empty:
        return {"count": 0, "total": 0.0, "share_pct": 0.0, "top_habits": pd.DataFrame()}

    # Group by brand/prefix keyword (e.g. Highlands, GrabBike, ShopeeFood, Phúc Long, Petrolimex)
    habit_patterns = [
        ("Cà phê & Trà sữa", ["highlands", "phúc long", "phuc long", "katinat", "starbucks", "mixue", "trà sữa", "coffee", "cà phê"]),
        ("Đặt đồ ăn / Bữa lẻ", ["grabfood", "shopeefood", "cơm ", "phở ", "bún ", "bánh mì", "circle k"]),
        ("Xe công nghệ & Xăng", ["grabbike", "xanh sm", "petrolimex", "đổ xăng", "grab "]),
        ("Gói đăng ký nhỏ", ["spotify", "icloud", "youtube"]),
    ]

    def _tag_habit(desc: str) -> str:
        low = f" {str(desc).lower()} "
        for label, kws in habit_patterns:
            if any(k in low for k in kws):
                return label
        return "Chi tiêu lẻ khác"

    micro["habit_group"] = micro["description"].map(_tag_habit)
    grouped = (
        micro.groupby("habit_group", as_index=False)
        .agg(tx_count=("amount", "count"), total=("amount", "sum"), avg_ticket=("amount", "mean"))
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )
    micro_total = float(micro["amount"].sum())
    return {
        "count": int(len(micro)),
        "total": micro_total,
        "share_pct": (micro_total / total_exp * 100.0) if total_exp > 0 else 0.0,
        "top_habits": grouped,
    }


def analyze_spending(
    df: pd.DataFrame,
    selected_month: str,
    fixed_expenses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run full Member 2 Spending Behavior Analysis for a selected month or entire history."""
    cur_exp = df.loc[df["type"] == "expense"].copy()
    if selected_month != "ALL":
        cur_exp = cur_exp.loc[cur_exp["year_month"] == selected_month].copy()

    total_exp = float(cur_exp["amount"].sum())
    if cur_exp.empty:
        breakdown = pd.DataFrame(columns=["category", "amount", "tx_count", "share_pct", "prev_amount", "change_pct"])
    else:
        breakdown = (
            cur_exp.groupby("category", as_index=False)
            .agg(amount=("amount", "sum"), tx_count=("amount", "count"))
            .sort_values("amount", ascending=False)
            .reset_index(drop=True)
        )
        breakdown["share_pct"] = (breakdown["amount"] / total_exp * 100.0) if total_exp > 0 else 0.0

        prev_month = get_previous_month(df, selected_month) if selected_month != "ALL" else None
        if prev_month:
            prev_exp = df.loc[(df["type"] == "expense") & (df["year_month"] == prev_month)]
            prev_map = prev_exp.groupby("category")["amount"].sum().to_dict()
            breakdown["prev_amount"] = breakdown["category"].map(lambda c: float(prev_map.get(c, 0.0)))
            breakdown["change_pct"] = np.where(
                breakdown["prev_amount"] > 0,
                (breakdown["amount"] - breakdown["prev_amount"]) / breakdown["prev_amount"] * 100.0,
                np.nan,
            )
        else:
            breakdown["prev_amount"] = 0.0
            breakdown["change_pct"] = np.nan

    spikes = []
    if not breakdown.empty and breakdown["change_pct"].notna().any():
        for _, row in breakdown.iterrows():
            chg = row["change_pct"]
            diff = float(row["amount"] - row["prev_amount"])
            if pd.notna(chg) and float(chg) >= 20.0 and diff >= 200_000:
                spikes.append(
                    {
                        "category": str(row["category"]),
                        "current": float(row["amount"]),
                        "previous": float(row["prev_amount"]),
                        "diff": diff,
                        "change_pct": float(chg),
                    }
                )
        spikes.sort(key=lambda x: x["change_pct"], reverse=True)

    all_exp = df.loc[df["type"] == "expense"].copy()
    monthly_cat = (
        all_exp.groupby(["year_month", "category"], as_index=False)["amount"]
        .sum()
        .sort_values("year_month")
    )

    recurring_df = detect_recurring_transactions(df, fixed_expenses)
    anomalies_df = detect_anomalies(df, selected_month)
    micro_info = detect_micro_spending(df, selected_month)

    top_category = str(breakdown.iloc[0]["category"]) if not breakdown.empty else "Other"
    top_category_amount = float(breakdown.iloc[0]["amount"]) if not breakdown.empty else 0.0
    top_category_share = float(breakdown.iloc[0]["share_pct"]) if not breakdown.empty else 0.0

    return {
        "total_expense": total_exp,
        "top_category": top_category,
        "top_category_amount": top_category_amount,
        "top_category_share": top_category_share,
        "category_breakdown": breakdown,
        "spikes": spikes,
        "monthly_category_trend": monthly_cat,
        "recurring": recurring_df,
        "anomalies": anomalies_df,
        "micro_spending": micro_info,
        "recurring_monthly_total": float(recurring_df["avg_amount"].sum()) if not recurring_df.empty else 0.0,
    }
