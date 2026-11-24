"""Vector SVG Icons, Brand Prism Logo & Mini Sparkline Charts (UI/UX Pro Max — Zero Emojis)."""

from __future__ import annotations

_SVG_PATHS: dict[str, str] = {
    "lens": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/><path d="M11 8v6M8 11h6"/>',
    "wallet": '<path d="M19 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2"/><path d="M21 12a2 2 0 0 0-2-2h-4a2 2 0 0 0 0 4h4a2 2 0 0 0 2-2Z"/>',
    "arrow_down_left": '<path d="M17 7 7 17"/><path d="M17 17H7V7"/>',
    "arrow_up_right": '<path d="M7 17 17 7"/><path d="M7 7h10v10"/>',
    "landmark": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/>',
    "credit_card": '<rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.5 12.9 17 22l-5-3-5 3 1.5-9.1"/>',
    "alert_triangle": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/>',
    "repeat": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    "trending_up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
    "receipt": '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 7h8M8 11h8M8 15h5"/>',
    "cpu": '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "coffee": '<path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><line x1="6" x2="6" y1="2" y2="4"/><line x1="10" x2="10" y1="2" y2="4"/><line x1="14" x2="14" y1="2" y2="4"/>',
    "shield_check": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "camera": '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/><circle cx="12" cy="13" r="3"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "pie_chart": '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
}


def icon_svg(name: str, color: str = "currentColor", size: int = 18) -> str:
    """Return crisp inline SVG icon string with consistent 1.85px stroke."""
    paths = _SVG_PATHS.get(name, _SVG_PATHS["sparkles"])
    return (
        f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.85" stroke-linecap="round" '
        f'stroke-linejoin="round" style="display:block;flex-shrink:0;">{paths}</svg>'
    )


def brand_logo_svg(size: int = 28) -> str:
    """Geometric Emerald-to-Indigo prism logo matching the reference MoneyLens AI header."""
    return (
        f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 32 32" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;flex-shrink:0;">'
        f'<defs>'
        f'<linearGradient id="mlPrismA" x1="2" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0%" stop-color="#34D399"/>'
        f'<stop offset="52%" stop-color="#3B82F6"/>'
        f'<stop offset="100%" stop-color="#8B5CF6"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<path d="M16 3L29 14.5L16 29L3 14.5L16 3Z" fill="url(#mlPrismA)" fill-opacity="0.92"/>'
        f'<path d="M16 3L29 14.5L16 17.5L3 14.5L16 3Z" fill="#FFFFFF" fill-opacity="0.22"/>'
        f'<path d="M16 3V29" stroke="#FFFFFF" stroke-opacity="0.35" stroke-width="1.2"/>'
        f'</svg>'
    )


def sparkline_svg(direction: str = "up") -> str:
    """Render clean inline mini sparkline curve for KPI cards (matching reference mockup)."""
    if direction == "down":
        return (
            '<svg aria-hidden="true" width="64" height="26" viewBox="0 0 64 26" fill="none">'
            '<path d="M2 8 C12 6, 18 15, 28 14 C38 13, 46 21, 58 20" stroke="#EF4444" stroke-width="2" stroke-linecap="round"/>'
            '<circle cx="58" cy="20" r="2.8" fill="#EF4444"/>'
            '</svg>'
        )
    return (
        '<svg aria-hidden="true" width="64" height="26" viewBox="0 0 64 26" fill="none">'
        '<path d="M2 21 C12 19, 18 12, 28 14 C38 16, 46 9, 58 5" stroke="#10B981" stroke-width="2" stroke-linecap="round"/>'
        '<circle cx="58" cy="5" r="2.8" fill="#10B981"/>'
        '</svg>'
    )


def google_logo_svg(size: int = 20) -> str:
    """Authentic 4-color Google 'G' vector mark for Google Sign-In CTA."""
    return (
        f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;flex-shrink:0;">'
        f'<path fill="#4285F4" d="M23.745 12.27c0-.79-.07-1.54-.19-2.27h-11.3v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82Z"/>'
        f'<path fill="#34A853" d="M12.255 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96h-3.98v3.09C3.515 21.3 7.565 24 12.255 24Z"/>'
        f'<path fill="#FBBC05" d="M5.525 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62h-3.98a11.86 11.86 0 0 0 0 10.76l3.98-3.09Z"/>'
        f'<path fill="#EA4335" d="M12.255 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C18.205 1.19 15.495 0 12.255 0c-4.69 0-8.74 2.7-10.71 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96Z"/>'
        f'</svg>'
    )
