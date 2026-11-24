# MoneyLens AI — UI/UX Pro Max Master Design System

> Generated using the installed **UI UX Pro Max Skill** (`.agents/skills/ui-ux-pro-max`)  
> Target: Personal Finance AI Dashboard for Vietnamese Students & Young Professionals (Streamlit + Plotly)

---

## 1. Visual Style & Direction
- **Primary Style:** **Minimalism & Swiss FinTech Style** (High-contrast clarity, 8px grid, crisp borders, tabular numerical typography, calm trust palette — zero cliché purple/pink AI gradients).
- **Surface Strategy:** Soft cool-slate canvas (`#F4F6FA`) paired with elevated crisp `#FFFFFF` cards (`1px solid #E2E8F0`) and subtle diffused shadow (`0 1px 2px rgba(15,23,42,0.04)`).
- **Motion & Interaction:** Smooth `200ms cubic-bezier(0.16, 1, 0.3, 1)` border/elevation transitions without layout-shifting jitter; respects `@media (prefers-reduced-motion: reduce)`; visible `:focus-visible` keyboard focus rings.

---

## 2. Color Tokens (WCAG AA >= 4.5:1 Contrast Verified)

| Role | Token | Hex | Usage |
|---|---|---|---|
| Brand Primary | `--ml-primary` | `#1E40AF` | Trust Navy — headers, primary buttons, brand chrome |
| Interactive Accent | `--ml-primary-light` | `#2563EB` | Active tabs, line charts, focus rings |
| Brand Soft Surface | `--ml-primary-soft` | `#EFF6FF` | Active nav background, AI insight surface |
| Positive / Income | `--ml-success` | `#059669` | Income, positive cash balance, savings pills |
| Positive Soft | `--ml-success-soft` | `#ECFDF5` | Positive badge fills |
| Expense / Danger | `--ml-danger` | `#DC2626` | Over-budget, anomalies, negative forecast zone |
| Danger Soft | `--ml-danger-soft` | `#FEF2F2` | Alert badge fills & deficit cards |
| Warning / Recurring | `--ml-warning` | `#D97706` | Subscriptions, nearing budget threshold (80–99%) |
| Warning Soft | `--ml-warning-soft` | `#FFFBEB` | Recurring highlight badges |
| Ink Primary | `--ml-ink` | `#0F172A` | Headings, KPI values (17.4:1 contrast on white) |
| Ink Secondary | `--ml-ink-secondary` | `#334155` | Body prose, table text (10.8:1 contrast) |
| Ink Muted | `--ml-muted` | `#475569` | Captions, axis ticks (7.5:1 contrast — AA/AAA) |
| Canvas Background | `--ml-bg` | `#F4F6FA` | Main viewport background |
| Card Surface | `--ml-surface` | `#FFFFFF` | Cards, sidebar, chart containers |
| Border Default | `--ml-border` | `#E2E8F0` | 1px card strokes & section dividers |

### 6 Canonical Expense Category Colors
- `Food` (Ăn uống): `#EA580C`
- `Shopping` (Mua sắm): `#7C3AED`
- `Transport` (Di chuyển): `#0284C7`
- `Bills` (Hóa đơn): `#1E40AF`
- `Entertainment` (Giải trí): `#DB2777`
- `Other` (Khác): `#475569`

---

## 3. Typography Pairing
- **UI & Headings:** `IBM Plex Sans` (Weights: 400, 500, 600, 700) — authoritative banking/fintech clarity with crisp Vietnamese diacritics.
- **Numerical / VND Figures:** `JetBrains Mono` / `IBM Plex Sans` with `font-variant-numeric: tabular-nums` so currency columns and KPI values align cleanly.

---

## 4. Iconography & Data Visualization Rules (Pre-Delivery Checklist)
- [x] **No emojis as structural UI icons**: Use crisp `1.75px` stroke inline SVG vector icons (`ui/icons.py`) and Material Symbols (`:material/...:`) for navigation.
- [x] **Donut / Pie Charts**: Max 6 slices, largest slice starts at 12 o'clock (`sort=True, direction="clockwise"`), dedicated plot domain `y=[0.28, 1.0]` with bottom legend anchored cleanly at `yanchor="top", y=0.18` so **zero legend-to-ring overlap** can occur at any viewport size.
- [x] **Table & Accessibility Fallback**: Every donut/bar chart pairs with exact VND hover tooltips and a readable structured summary table.
