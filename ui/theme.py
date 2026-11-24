"""Dual-Theme (Light/Dark) Swiss FinTech Design System matching Reference Mockup & Floating AI Chat."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.i18n import cat_label, t

# ---------------------------------------------------------------------------
# Dual-Theme Semantic Palettes (Light Mode matches reference screenshot 1:1;
# Dark Mode gives sleek midnight FinTech contrast >= 4.5:1)
# ---------------------------------------------------------------------------
LIGHT_PALETTE = {
    "primary": "#2563EB",
    "primary_dark": "#1E40AF",
    "primary_light": "#3B82F6",
    "primary_soft": "#EFF6FF",
    "primary_border": "#BFDBFE",
    "accent": "#0284C7",
    "success": "#059669",
    "success_dark": "#047857",
    "success_soft": "#ECFDF5",
    "success_border": "#A7F3D0",
    "danger": "#DC2626",
    "danger_dark": "#B91C1C",
    "danger_soft": "#FEF2F2",
    "danger_border": "#FECACA",
    "warning": "#D97706",
    "warning_dark": "#B45309",
    "warning_soft": "#FFFBEB",
    "warning_border": "#FDE68A",
    "ink": "#0F172A",
    "ink_secondary": "#334155",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",
    "bg": "#F4F6FA",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "subnav_bg": "#FFFFFF",
    "topbar_bg": "#0F172A",
    "grid": "#EEF2F6",
    "donut_ring_border": "#FFFFFF",
}

DARK_PALETTE = {
    "primary": "#60A5FA",
    "primary_dark": "#3B82F6",
    "primary_light": "#93C5FD",
    "primary_soft": "#172554",
    "primary_border": "#1E40AF",
    "accent": "#38BDF8",
    "success": "#34D399",
    "success_dark": "#10B981",
    "success_soft": "#064E3B",
    "success_border": "#047857",
    "danger": "#F87171",
    "danger_dark": "#EF4444",
    "danger_soft": "#450A0A",
    "danger_border": "#991B1B",
    "warning": "#FBBF24",
    "warning_dark": "#F59E0B",
    "warning_soft": "#451A03",
    "warning_border": "#92400E",
    "ink": "#F8FAFC",
    "ink_secondary": "#CBD5E1",
    "muted": "#94A3B8",
    "border": "#1E293B",
    "border_strong": "#334155",
    "bg": "#0B1120",
    "surface": "#111827",
    "surface_alt": "#1E293B",
    "subnav_bg": "#111827",
    "topbar_bg": "#060A14",
    "grid": "#1E293B",
    "donut_ring_border": "#111827",
}

# Keep COLORS exported for backward compatibility (defaults to Light)
COLORS = LIGHT_PALETTE

CATEGORY_COLORS = {
    "Shopping": "#7C3AED",      # Vibrant Violet (matches mockup 42.1% slice)
    "Bills": "#2563EB",         # Royal Blue (matches mockup 36.7% slice)
    "Food": "#F97316",          # Warm Orange (matches mockup 14.2% slice)
    "Entertainment": "#10B981", # Emerald Green (matches mockup 4.2% slice)
    "Transport": "#0EA5E9",     # Sky Blue
    "Other": "#94A3B8",         # Neutral Slate
    "Income": "#059669",
}

EXPENSE_CATEGORIES = ["Food", "Shopping", "Transport", "Bills", "Entertainment", "Other"]


def get_palette(theme_mode: str = "light") -> dict[str, str]:
    """Return active theme palette dict ('light' or 'dark')."""
    return DARK_PALETTE if theme_mode == "dark" else LIGHT_PALETTE


def get_category_label(category: str, with_icon: bool = False, lang: str = "vi") -> str:
    return cat_label(category, lang=lang)


def get_category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#64748B")


def format_vnd(amount: float | int, show_sign: bool = False, compact: bool = False) -> str:
    """Format numeric amount in Vietnamese Dong (VND)."""
    if amount is None:
        return "0 ₫"
    value = float(amount)
    sign = ""
    if show_sign:
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "-"
    elif value < 0:
        sign = "-"

    abs_val = abs(value)
    if compact:
        if abs_val >= 1_000_000_000:
            return f"{sign}{abs_val / 1_000_000_000:.2f} tỷ ₫"
        if abs_val >= 1_000_000:
            return f"{sign}{abs_val / 1_000_000:.2f} tr ₫"
        if abs_val >= 1_000:
            return f"{sign}{abs_val / 1_000:.0f}k ₫"
    formatted = f"{int(round(abs_val)):,}".replace(",", ".")
    return f"{sign}{formatted} ₫"


def apply_plotly_theme(
    fig: go.Figure,
    height: int = 330,
    show_legend: bool = True,
    theme_mode: str = "light",
) -> go.Figure:
    """Apply Light/Dark FinTech styling to Plotly charts."""
    p = get_palette(theme_mode)
    fig.update_layout(
        font=dict(family="IBM Plex Sans, -apple-system, sans-serif", color=p["ink"], size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=14, r=14, t=28, b=18),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11.5, color=p["muted"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="#0F172A" if theme_mode == "light" else "#F8FAFC",
            font_size=12,
            font_family="IBM Plex Sans, sans-serif",
            font_color="#FFFFFF" if theme_mode == "light" else "#0F172A",
        ),
    )
    fig.update_xaxes(showgrid=False, linecolor=p["border"], tickfont=dict(color=p["muted"], size=11), zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=p["grid"], gridwidth=1, tickfont=dict(color=p["muted"], size=11), zeroline=False)
    return fig


def build_clean_donut_figure(
    breakdown: pd.DataFrame,
    total_expense: float,
    height: int = 290,
    theme_mode: str = "light",
    lang: str = "vi",
) -> go.Figure:
    """Build Donut-Left + Right-Side Vertical Legend matching reference mockup (0% overlap!)."""
    p = get_palette(theme_mode)
    sorted_bd = breakdown.sort_values("amount", ascending=False).reset_index(drop=True)
    # Include percentage right in the legend label like the reference screenshot!
    legend_labels = [
        f"{cat_label(c, lang)}   <b>{pct:.1f}%</b>"
        for c, pct in zip(sorted_bd["category"], sorted_bd["share_pct"])
    ]
    colors = [get_category_color(c) for c in sorted_bd["category"]]
    shares = sorted_bd["share_pct"].tolist()
    clean_text = [f"{pct:.1f}%" if pct >= 7.0 else "" for pct in shares]

    fig = go.Figure(
        go.Pie(
            labels=legend_labels,
            values=sorted_bd["amount"],
            hole=0.67,
            sort=True,
            direction="clockwise",
            domain=dict(x=[0.0, 0.54], y=[0.04, 0.96]),
            marker=dict(colors=colors, line=dict(color=p["donut_ring_border"], width=2.5)),
            text=clean_text,
            textinfo="text",
            textposition="inside",
            insidetextorientation="horizontal",
            insidetextfont=dict(color="#FFFFFF", size=11, family="IBM Plex Sans, sans-serif"),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} ₫<extra></extra>",
        )
    )
    fig.add_annotation(
        text=(
            f"<b style='font-size:11.5px;color:{p['ink']};'>{format_vnd(total_expense, compact=True)}</b>"
            f"<br><span style='font-size:9.5px;color:{p['muted']};'>{t('total_spend_lbl', lang)}</span>"
        ),
        x=0.27,
        y=0.50,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="center",
    )
    apply_plotly_theme(fig, height=height, show_legend=True, theme_mode=theme_mode)
    fig.update_layout(
        margin=dict(l=4, r=4, t=8, b=8),
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.50,
            xanchor="left",
            x=0.58,
            font=dict(size=12, color=p["ink_secondary"]),
            itemsizing="constant",
            tracegroupgap=6,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def inject_global_css(theme_mode: str = "light") -> None:
    """Inject full Light/Dark CSS matching reference topbar + subnav + workspace + floating circular AI bot."""
    p = get_palette(theme_mode)
    is_dark = theme_mode == "dark"
    input_bg = "#1E293B" if is_dark else "#FFFFFF"
    placeholder_color = "#94A3B8" if is_dark else "#64748B"
    btn_bg = "#1E293B" if is_dark else "#FFFFFF"
    btn_hover_bg = "#172554" if is_dark else "#EFF6FF"
    card_shadow = "0 4px 16px rgba(0,0,0,0.32)" if is_dark else "0 1px 3px rgba(15, 23, 42, 0.05)"
    topbar_btn_bg = "rgba(255,255,255,0.10)"
    topbar_btn_border = "rgba(255,255,255,0.22)"
    code_bg = "#0F172A" if is_dark else "#F1F5F9"
    code_ink = "#E2E8F0" if is_dark else "#0F172A"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

        :root {{
            --ml-primary: {p['primary']};
            --ml-primary-soft: {p['primary_soft']};
            --ml-success: {p['success']};
            --ml-danger: {p['danger']};
            --ml-warning: {p['warning']};
            --ml-ink: {p['ink']};
            --ml-ink-sec: {p['ink_secondary']};
            --ml-muted: {p['muted']};
            --ml-bg: {p['bg']};
            --ml-surface: {p['surface']};
            --ml-surface-alt: {p['surface_alt']};
            --ml-border: {p['border']};
            --ml-border-strong: {p['border_strong']};
        }}

        html, body, [class*="css"] {{
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--ml-ink);
            -webkit-font-smoothing: antialiased;
        }}

        .stApp {{
            background-color: var(--ml-bg) !important;
            color: var(--ml-ink) !important;
            overflow-x: hidden !important;
        }}

        /* Hide default Streamlit chrome & sidebar to match bespoke Topbar + Subnav mockup */
        header[data-testid="stHeader"] {{ display: none !important; }}
        section[data-testid="stSidebar"] {{ display: none !important; }}
        button[data-testid="collapsedControl"] {{ display: none !important; }}
        #MainMenu, footer {{ visibility: hidden; }}

        div[data-testid="stMainBlockContainer"],
        .block-container {{
            padding-top: 0 !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-bottom: 5rem !important;
            max-width: 100% !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }}

        /* ==============================================================
           DUAL-THEME (DARK & LIGHT) NATIVE WIDGET & PLACEHOLDER FIXES
           ============================================================== */
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li,
        div[data-testid="stMarkdownContainer"] h1,
        div[data-testid="stMarkdownContainer"] h2,
        div[data-testid="stMarkdownContainer"] h3,
        div[data-testid="stMarkdownContainer"] h4,
        div[data-testid="stMarkdownContainer"] h5,
        div[data-testid="stWidgetLabel"] p,
        div[data-testid="stCheckbox"] label p,
        label {{
            color: var(--ml-ink);
        }}
        div[data-testid="stCaptionContainer"] p {{
            color: var(--ml-muted) !important;
        }}

        /* Fix BaseWeb input/textarea/select wrappers & remove white seam in Dark Mode */
        div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="textarea"],
        div[data-baseweb="select"],
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            color: var(--ml-ink) !important;
            border-color: var(--ml-border-strong) !important;
            box-shadow: none !important;
        }}
        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="textarea"]:focus-within,
        div[data-baseweb="select"]:focus-within > div {{
            border-color: var(--ml-primary) !important;
            box-shadow: 0 0 0 1px var(--ml-primary) !important;
        }}
        input, textarea, select {{
            background-color: {input_bg} !important;
            color: var(--ml-ink) !important;
            caret-color: var(--ml-ink) !important;
            -webkit-text-fill-color: var(--ml-ink) !important;
        }}
        /* HIGH-CONTRAST PLACEHOLDERS IN DARK & LIGHT MODE */
        input::placeholder,
        textarea::placeholder,
        input::-webkit-input-placeholder,
        textarea::-webkit-input-placeholder,
        div[data-baseweb="input"] input::placeholder,
        div[data-baseweb="textarea"] textarea::placeholder,
        div[data-testid="stTextInput"] input::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder,
        div[data-testid="stChatInput"] textarea::placeholder {{
            color: {placeholder_color} !important;
            opacity: 1 !important;
            -webkit-text-fill-color: {placeholder_color} !important;
        }}
        /* Selectbox & Multiselect inner text, chevron box & dropdown popups */
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] > div * {{
            background-color: {input_bg} !important;
        }}
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div[value],
        div[data-baseweb="select"] svg {{
            color: var(--ml-ink) !important;
            fill: var(--ml-muted) !important;
        }}
        div[data-baseweb="popover"] ul[role="listbox"],
        ul[data-testid="stSelectboxVirtualDropdown"] {{
            background-color: var(--ml-surface) !important;
            border: 1px solid var(--ml-border-strong) !important;
        }}
        div[data-baseweb="popover"] li[role="option"],
        ul[data-testid="stSelectboxVirtualDropdown"] li {{
            background-color: var(--ml-surface) !important;
            color: var(--ml-ink) !important;
        }}
        div[data-baseweb="popover"] li[role="option"]:hover,
        ul[data-testid="stSelectboxVirtualDropdown"] li:hover {{
            background-color: var(--ml-primary-soft) !important;
            color: var(--ml-primary) !important;
        }}
        /* Segmented controls (Cash Flow toggle & Spending trend toggle) in Dark & Light Mode */
        div[data-testid="stButtonGroup"] button,
        button[data-testid="stBaseButton-segmented_control"],
        button[data-testid="stBaseButton-pills"] {{
            background-color: var(--ml-surface-alt) !important;
            color: var(--ml-ink-sec) !important;
            border: 1px solid var(--ml-border-strong) !important;
        }}
        div[data-testid="stButtonGroup"] button *,
        button[data-testid="stBaseButton-segmented_control"] * {{
            color: var(--ml-ink-sec) !important;
        }}
        div[data-testid="stButtonGroup"] button[aria-pressed="true"],
        button[data-testid="stBaseButton-segmented_controlActive"],
        button[data-testid="stBaseButton-pillsActive"] {{
            background-color: var(--ml-primary-soft) !important;
            color: var(--ml-primary) !important;
            border: 1px solid {p['primary_border']} !important;
        }}
        div[data-testid="stButtonGroup"] button[aria-pressed="true"] *,
        button[data-testid="stBaseButton-segmented_controlActive"] * {{
            color: var(--ml-primary) !important;
            font-weight: 600 !important;
        }}
        /* st.success / st.info / st.warning / st.error Alert boxes in Dark & Light Mode */
        div[data-testid="stAlert"],
        div[data-testid="stAlertContainer"] {{
            background-color: {p['surface_alt'] if is_dark else p['primary_soft']} !important;
            border: 1px solid {p['border_strong'] if is_dark else p['primary_border']} !important;
            border-radius: 11px !important;
            color: var(--ml-ink) !important;
        }}
        div[data-testid="stAlert"] *,
        div[data-testid="stAlertContainer"] * {{
            color: var(--ml-ink) !important;
        }}
        /* Native Dual-Theme FinTech Transaction Table */
        .ml-tx-table-wrap {{
            width: 100%;
            max-height: 320px;
            overflow-y: auto;
            border: 1px solid var(--ml-border);
            border-radius: 11px;
            background: var(--ml-surface);
        }}
        .ml-tx-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
            color: var(--ml-ink);
        }}
        .ml-tx-table thead th {{
            position: sticky;
            top: 0;
            background: var(--ml-surface-alt);
            color: var(--ml-muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            text-align: left;
            padding: 9px 12px;
            border-bottom: 1px solid var(--ml-border);
            z-index: 1;
        }}
        .ml-tx-table tbody td {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--ml-border);
            color: var(--ml-ink);
            vertical-align: middle;
        }}
        .ml-tx-table tbody tr:hover {{
            background: var(--ml-surface-alt);
        }}
        .ml-tx-table tbody tr:last-child td {{
            border-bottom: none;
        }}
        /* Number input +/- buttons & chat input in Dark Mode */
        button[data-testid="stNumberInputStepUp"],
        button[data-testid="stNumberInputStepDown"] {{
            background-color: var(--ml-surface-alt) !important;
            color: var(--ml-ink) !important;
            border-color: var(--ml-border-strong) !important;
        }}
        button[data-testid="stNumberInputStepUp"] svg,
        button[data-testid="stNumberInputStepDown"] svg {{
            fill: var(--ml-ink) !important;
            color: var(--ml-ink) !important;
        }}
        div[data-testid="stChatInput"] > div {{
            background-color: {input_bg} !important;
            border-color: var(--ml-border-strong) !important;
        }}
        /* Tabs & Code blocks in Dark Mode */
        button[data-baseweb="tab"] p {{
            color: var(--ml-muted) !important;
            font-weight: 600 !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: var(--ml-primary) !important;
        }}
        div[data-testid="stCodeBlock"] pre,
        pre, code {{
            background-color: {code_bg} !important;
            color: {code_ink} !important;
        }}
        div[data-testid="stFileUploaderDropzone"] {{
            background-color: var(--ml-surface-alt) !important;
            border-color: var(--ml-border-strong) !important;
            color: var(--ml-ink) !important;
        }}
        div[data-testid="stChatMessage"] {{
            background-color: var(--ml-surface) !important;
            border: 1px solid var(--ml-border) !important;
            border-radius: 14px !important;
        }}
        div[data-testid="stExpander"] {{
            background-color: var(--ml-surface) !important;
            border-color: var(--ml-border) !important;
            border-radius: 12px !important;
        }}
        div[data-testid="stExpander"] summary span,
        div[data-testid="stExpander"] summary p {{
            color: var(--ml-ink) !important;
        }}
        div[data-testid="stDialog"] div[role="dialog"] {{
            background-color: var(--ml-surface) !important;
            color: var(--ml-ink) !important;
        }}

        /* ==============================================================
           HORIZONTAL SUB-NAV BAR (Matches reference screenshot Row 2)
           ============================================================== */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker),
        div[data-testid="stVerticalBlock"]:has(> div.element-container .ml-subnav-marker) {{
            background: {p['subnav_bg']};
            margin-left: -1.5rem !important;
            margin-right: -1.5rem !important;
            width: calc(100% + 3rem) !important;
            max-width: none !important;
            box-sizing: border-box !important;
            padding: 8px 24px 8px 24px;
            border-bottom: 1px solid var(--ml-border);
            margin-bottom: 18px;
        }}

        /* Brand & User Avatar Pills in Top Bar */
        .ml-top-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding-top: 2px;
        }}
        .ml-top-brand-name {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #FFFFFF !important;
            letter-spacing: -0.02em;
        }}
        .ml-user-chip {{
            display: inline-flex;
            align-items: center;
            gap: 9px;
            padding: 4px 12px 4px 5px;
            border-radius: 999px;
            background: rgba(255,255,255,0.09);
            border: 1px solid rgba(255,255,255,0.18);
            color: #F8FAFC;
            max-width: 100%;
        }}
        .ml-avatar-circle {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563EB, #10B981);
            color: #FFFFFF;
            font-weight: 700;
            font-size: 0.76rem;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            overflow: hidden;
        }}
        .ml-avatar-circle img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .ml-pro-tag {{
            font-size: 0.65rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 999px;
            background: rgba(16, 185, 129, 0.22);
            color: #34D399 !important;
            border: 1px solid rgba(52, 211, 153, 0.35);
            display: inline-block;
        }}

        /* Bordered Surface Cards */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: var(--ml-surface) !important;
            border-color: var(--ml-border) !important;
            border-radius: 14px !important;
            box-shadow: {card_shadow};
        }}

        /* KPI Cards with Sparkline */
        .ml-kpi-card {{
            background: var(--ml-surface);
            border: 1px solid var(--ml-border);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: {card_shadow};
            transition: border-color 180ms ease, box-shadow 180ms ease;
            height: 100%;
        }}
        .ml-kpi-card:hover {{
            border-color: var(--ml-border-strong);
        }}
        .ml-kpi-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .ml-kpi-label {{
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--ml-muted) !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .ml-kpi-icon {{
            width: 30px;
            height: 30px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .ml-kpi-value {{
            font-variant-numeric: tabular-nums;
            font-size: 1.42rem;
            font-weight: 700;
            color: var(--ml-ink) !important;
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin-bottom: 8px;
        }}
        .ml-kpi-bottom {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 8px;
        }}
        .ml-kpi-meta {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .ml-kpi-note {{
            font-size: 0.74rem;
            color: var(--ml-muted) !important;
        }}

        /* Semantic Pills */
        .ml-pill {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 2px 9px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            line-height: 1.3;
            white-space: nowrap;
            width: fit-content;
        }}
        .ml-pill-success {{ background: {p['success_soft']}; color: {p['success_dark']}; border: 1px solid {p['success_border']}; }}
        .ml-pill-danger  {{ background: {p['danger_soft']}; color: {p['danger_dark']}; border: 1px solid {p['danger_border']}; }}
        .ml-pill-warning {{ background: {p['warning_soft']}; color: {p['warning_dark']}; border: 1px solid {p['warning_border']}; }}
        .ml-pill-primary {{ background: {p['primary_soft']}; color: {p['primary']}; border: 1px solid {p['primary_border']}; }}
        .ml-pill-neutral {{ background: {p['surface_alt']}; color: {p['ink_secondary']}; border: 1px solid {p['border']}; }}

        /* Page Title & Section Headers */
        h1.ml-page-title, .ml-page-title {{
            font-size: 1.52rem !important;
            font-weight: 700 !important;
            color: var(--ml-ink) !important;
            letter-spacing: -0.025em !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
        }}
        .ml-page-subtitle {{
            font-size: 0.88rem;
            color: var(--ml-muted) !important;
            margin-top: 3px;
        }}
        .ml-card-title {{
            font-size: 0.96rem;
            font-weight: 700;
            color: var(--ml-ink) !important;
            margin: 0 0 3px 0;
            display: flex;
            align-items: center;
            gap: 7px;
        }}
        .ml-card-caption {{
            font-size: 0.79rem;
            color: var(--ml-muted) !important;
            margin: 0 0 10px 0;
            line-height: 1.4;
        }}

        /* AI Insight Callout Banner */
        .ml-ai-banner {{
            background: {p['primary_soft']};
            border: 1px solid {p['primary_border']};
            border-left: 4px solid {p['primary']};
            border-radius: 12px;
            padding: 13px 16px;
            margin: 14px 0 16px 0;
        }}
        .ml-ai-banner-title {{
            font-size: 0.84rem;
            font-weight: 700;
            color: {p['primary']} !important;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .ml-ai-banner-body {{
            font-size: 0.85rem;
            color: var(--ml-ink-sec) !important;
            line-height: 1.52;
        }}

        /* Alert / List Items */
        .ml-list-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 11px 13px;
            border-radius: 11px;
            border: 1px solid var(--ml-border);
            background: var(--ml-surface-alt);
            margin-bottom: 9px;
        }}
        .ml-list-item-danger  {{ border-left: 3.5px solid {p['danger']}; }}
        .ml-list-item-primary {{ border-left: 3.5px solid {p['primary']}; }}
        .ml-list-item-warning {{ border-left: 3.5px solid {p['warning']}; }}
        .ml-list-item-success {{ border-left: 3.5px solid {p['success']}; }}

        .ml-progress-track {{
            width: 100%;
            height: 7px;
            background: var(--ml-border);
            border-radius: 999px;
            overflow: hidden;
            margin: 6px 0 8px 0;
        }}
        .ml-progress-fill {{
            height: 100%;
            border-radius: 999px;
        }}
        .ml-num {{ font-variant-numeric: tabular-nums; }}

        /* Google Auth & Onboarding Hero Helpers */
        .ml-google-oauth-link {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 11px 16px;
            border-radius: 11px;
            background: #FFFFFF;
            color: #0F172A !important;
            border: 1px solid #CBD5E1;
            font-weight: 600;
            font-size: 0.92rem;
            text-decoration: none !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
            transition: transform 140ms ease, box-shadow 140ms ease;
        }}
        .ml-google-oauth-link:hover {{
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.18);
            border-color: #2563EB;
        }}
        .ml-feature-row {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 12px 14px;
            border-radius: 12px;
            background: var(--ml-surface);
            border: 1px solid var(--ml-border);
            margin-bottom: 10px;
        }}
        .ml-live-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10B981;
            display: inline-block;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25);
        }}

        /* ==============================================================
           STANDARD BUTTONS (Primary / Secondary / Tertiary)
           ============================================================== */
        button {{
            cursor: pointer !important;
        }}
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-primaryFormSubmit"] {{
            background-color: {p['primary_dark']} !important;
            color: #FFFFFF !important;
            border: 1px solid {p['primary_dark']} !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }}
        button[data-testid="stBaseButton-primary"] *,
        button[data-testid="stBaseButton-primaryFormSubmit"] * {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }}
        button[data-testid="stBaseButton-secondary"],
        button[data-testid="stBaseButton-secondaryFormSubmit"] {{
            background-color: {btn_bg} !important;
            color: var(--ml-ink) !important;
            border: 1px solid var(--ml-border-strong) !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
        }}
        button[data-testid="stBaseButton-secondary"] *,
        button[data-testid="stBaseButton-secondaryFormSubmit"] * {{
            color: var(--ml-ink) !important;
        }}
        button[data-testid="stBaseButton-secondary"]:hover,
        button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {{
            border-color: var(--ml-primary) !important;
            background-color: {btn_hover_bg} !important;
        }}
        button[data-testid="stBaseButton-secondary"]:hover *,
        button[data-testid="stBaseButton-secondaryFormSubmit"]:hover * {{
            color: var(--ml-primary) !important;
        }}
        button[data-testid="stBaseButton-tertiary"] * {{
            color: var(--ml-ink-sec) !important;
        }}

        /* ==============================================================
           SUB-NAV BUTTON OVERRIDES (Placed AFTER standard button rules!)
           ============================================================== */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker) button[data-testid="stBaseButton-tertiary"] {{
            color: var(--ml-muted) !important;
            font-weight: 500 !important;
            font-size: 0.86rem !important;
            border-radius: 8px !important;
            padding: 0.4rem 0.68rem !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker) button[data-testid="stBaseButton-tertiary"] * {{
            color: var(--ml-muted) !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker) button[data-testid="stBaseButton-tertiary"]:hover {{
            background: var(--ml-primary-soft) !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker) button[data-testid="stBaseButton-tertiary"]:hover * {{
            color: var(--ml-primary) !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker) button[data-testid="stBaseButton-primary"] {{
            background: var(--ml-primary-soft) !important;
            color: var(--ml-primary) !important;
            border: 1px solid {p['primary_border']} !important;
            border-bottom: 2.5px solid var(--ml-primary) !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
            font-size: 0.86rem !important;
            padding: 0.4rem 0.78rem !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-subnav-marker) button[data-testid="stBaseButton-primary"] * {{
            color: var(--ml-primary) !important;
        }}

        /* ==============================================================
           TOP DARK NAVY GLOBAL BAR (Placed LAST so icons & text stay 100% CRISP WHITE!)
           ============================================================== */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker),
        div[data-testid="stVerticalBlock"]:has(> div.element-container .ml-topbar-marker) {{
            background: linear-gradient(90deg, #0B1120 0%, #0F172A 55%, #111D38 100%);
            margin-left: -1.5rem !important;
            margin-right: -1.5rem !important;
            width: calc(100% + 3rem) !important;
            max-width: none !important;
            box-sizing: border-box !important;
            padding: 10px 24px 10px 24px;
            border-bottom: 1px solid rgba(255,255,255,0.10);
        }}
        div[data-testid="stLayoutWrapper"]:has(.ml-topbar-marker),
        div[data-testid="stLayoutWrapper"]:has(.ml-subnav-marker) {{
            max-width: none !important;
            overflow: visible !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button,
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button[data-testid^="stBaseButton-"],
        div[data-testid="stVerticalBlock"]:has(> div.element-container .ml-topbar-marker) button {{
            background: {topbar_btn_bg} !important;
            color: #F8FAFC !important;
            border: 1px solid {topbar_btn_border} !important;
            border-radius: 9px !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            padding: 0.36rem 0.72rem !important;
            min-height: 36px !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button *,
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button p,
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button span,
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button span[data-testid="stIconMaterial"],
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button svg {{
            color: #F8FAFC !important;
            fill: #F8FAFC !important;
            opacity: 1 !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button:hover {{
            background: rgba(59, 130, 246, 0.32) !important;
            border-color: #60A5FA !important;
            color: #FFFFFF !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-topbar-marker) button:hover * {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }}

        /* ==============================================================
           FLOATING CIRCULAR AI HELP WIDGET (Bottom-Right Corner!)
           ============================================================== */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) {{
            position: fixed !important;
            bottom: 24px !important;
            right: 26px !important;
            z-index: 9999 !important;
            width: 58px !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) div[data-testid="stPopover"] button {{
            width: 58px !important;
            height: 58px !important;
            min-height: 58px !important;
            min-width: 58px !important;
            padding: 0 !important;
            border-radius: 9999px !important;
            background: linear-gradient(135deg, #1E40AF 0%, #2563EB 55%, #059669 100%) !important;
            color: #FFFFFF !important;
            border: 2px solid rgba(255,255,255,0.4) !important;
            box-shadow: 0 12px 28px -4px rgba(30, 64, 175, 0.58) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: transform 180ms ease, box-shadow 180ms ease !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) div[data-testid="stPopover"] button:hover {{
            transform: scale(1.07) !important;
            box-shadow: 0 16px 34px -4px rgba(37, 99, 235, 0.72) !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) div[data-testid="stPopover"] button *,
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) div[data-testid="stPopover"] button span,
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) div[data-testid="stPopover"] button p {{
            color: #FFFFFF !important;
            font-size: 1.4rem !important;
            margin: 0 !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ml-fab-marker) div[data-testid="stPopover"] button svg {{
            display: none !important;
        }}
        div[data-testid="stPopoverBody"] {{
            background-color: var(--ml-surface) !important;
            border: 1px solid var(--ml-border-strong) !important;
            border-radius: 16px !important;
            min-width: 350px !important;
            max-width: 400px !important;
            box-shadow: 0 20px 50px -12px rgba(15, 23, 42, 0.35) !important;
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{ transition-duration: 0.01ms !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
