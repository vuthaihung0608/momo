"""Top Deep Navy Header, Google Sign-In, Personal Onboarding, Sub-Nav & Real-Time Legal Bank Auto-Sync Panel."""

from __future__ import annotations

import hashlib
import html
import secrets

import pandas as pd
import streamlit as st

from src.auth import (
    authenticate_user,
    complete_user_onboarding,
    create_user_session,
    delete_user_session,
    get_google_oauth_url,
    is_google_oauth_configured,
    list_google_accounts,
    regenerate_webhook_token,
    register_user,
    sign_in_with_google_profile,
    update_user_budget,
    update_user_profile,
)
from src.capture import (
    SAMPLE_BANK_NOTIFICATIONS,
    parse_bank_notification,
    parse_bill_image,
    parse_quick_text,
)
from src.data_processing import (
    get_email_sync_config,
    get_recent_webhook_events,
    insert_transaction,
    set_app_setting,
)
from src.email_bank_sync import (
    SAMPLE_BANK_EMAILS,
    import_selected_bank_transactions,
    preview_user_bank_emails,
    save_and_test_email_config,
    scan_user_bank_emails_now,
    simulate_bank_email_preview,
    simulate_bank_email_scan,
)
from src.webhook_server import (
    get_webhook_base_url,
    get_webhook_port,
    is_webhook_server_healthy,
    send_live_test_webhook,
)
from ui.i18n import cat_label, fmt_month_label, t
from ui.icons import brand_logo_svg, google_logo_svg, icon_svg
from ui.theme import EXPENSE_CATEGORIES, format_vnd, get_palette

OCCUPATION_OPTIONS = {
    "vi": [
        "Sinh viên đại học",
        "Người trẻ mới đi làm",
        "Freelancer / Tự do",
        "Nhân viên văn phòng",
        "Kinh doanh cá nhân",
        "Khác",
    ],
    "en": [
        "University Student",
        "Young Professional",
        "Freelancer",
        "Office Staff / Manager",
        "Small Business Owner",
        "Other",
    ],
}

GOAL_OPTIONS = {
    "vi": [
        "Kiểm soát chi tiêu cuối tháng & tránh thâm hụt",
        "Xây quỹ dự phòng (3–6 tháng chi phí)",
        "Tiết kiệm mua sắm lớn (Laptop, xe, du lịch)",
        "Cắt giảm khoản chi nhỏ lặp lại & gói định kỳ thừa",
    ],
    "en": [
        "Control month-end spending & stay within budget",
        "Build a 3–6 month emergency fund",
        "Save for a big purchase (Laptop, vehicle, travel)",
        "Cut micro-spending leaks & unused subscriptions",
    ],
}

BANK_CHOICES = [
    "MBBank",
    "Vietcombank",
    "Techcombank",
    "ACB",
    "TPBank",
    "VPBank",
    "BIDV",
    "VietinBank",
    "MoMo",
    "ZaloPay",
]

AVATAR_GRADIENTS = [
    "linear-gradient(135deg, #2563EB, #10B981)",
    "linear-gradient(135deg, #7C3AED, #EC4899)",
    "linear-gradient(135deg, #0284C7, #14B8A6)",
    "linear-gradient(135deg, #EA580C, #F59E0B)",
    "linear-gradient(135deg, #4F46E5, #06B6D4)",
    "linear-gradient(135deg, #059669, #84CC16)",
]


def _avatar_gradient_for(email: str) -> str:
    idx = int(hashlib.md5(email.encode("utf-8")).hexdigest()[:8], 16) % len(AVATAR_GRADIENTS)
    return AVATAR_GRADIENTS[idx]


def _initials_for(full_name: str, email: str) -> str:
    words = [w for w in str(full_name or "").strip().split() if w]
    if len(words) >= 2:
        return (words[0][0] + words[-1][0]).upper()
    if len(words) == 1:
        return words[0][:2].upper()
    return (str(email or "ML")[:2]).upper()


def _reset_session_for_user(user: dict, lang: str) -> None:
    st.session_state["current_user"] = user
    st.session_state["monthly_budget"] = int(user["monthly_budget"])
    st.session_state["force_reload_db"] = True
    st.session_state["selected_month"] = None
    st.session_state.pop("db_sync_sig", None)
    st.session_state.pop("pending_bill", None)
    st.session_state.pop("pending_bank", None)
    st.session_state.pop("bank_sync_preview", None)
    st.session_state["show_bank_preview_modal"] = False
    st.query_params["sid"] = create_user_session(user["id"])
    display = user["full_name"] or user["email"]
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                f"Xin chào **{display}**! Mình là **MoneyLens AI** — trợ lý AI toàn năng có thể trả lời mọi câu hỏi (tài chính cá nhân, đầu tư, học tập, công việc, đời sống...) đồng thời nắm rõ dữ liệu giao dịch của riêng bạn.\n\n"
                "Bạn có thể hỏi bất cứ điều gì ở ô nhập bên dưới hoặc bấm câu hỏi gợi ý bên trên!"
                if lang == "vi"
                else f"Hello **{display}**! I'm **MoneyLens AI** — an all-purpose AI assistant grounded in your personal finance data. Ask me anything!"
            ),
            "chart": None,
            "source": "MoneyLens AI",
        }
    ]


def _sign_out_user() -> None:
    sid = st.query_params.get("sid")
    sid_str = sid[0] if isinstance(sid, list) else str(sid or "")
    if sid_str:
        delete_user_session(sid_str)
    st.query_params.pop("sid", None)
    for k in (
        "current_user",
        "transactions_df",
        "selected_month",
        "db_sync_sig",
        "pending_bill",
        "pending_bank",
        "bank_sync_preview",
        "show_bank_preview_modal",
        "chat_messages",
        "last_capture_feedback",
    ):
        st.session_state.pop(k, None)
    st.session_state["force_reload_db"] = True
    st.session_state["active_page"] = "overview"


def _dismiss_bank_preview_modal() -> None:
    st.session_state["show_bank_preview_modal"] = False


def _open_bank_preview_batch(preview_res: dict) -> None:
    batch_id = int(st.session_state.get("bank_preview_batch_id", 0)) + 1
    st.session_state["bank_preview_batch_id"] = batch_id
    st.session_state["bank_sync_preview"] = preview_res
    for idx in range(len(preview_res.get("candidates") or [])):
        st.session_state[f"bs_chk_{batch_id}_{idx}"] = True
    st.session_state["show_bank_preview_modal"] = True


def _set_all_preview_checks(batch_id: int, total: int, checked: bool) -> None:
    for idx in range(total):
        st.session_state[f"bs_chk_{batch_id}_{idx}"] = checked


def _fmt_preview_ts(ts: str, fallback_date: str = "") -> str:
    raw = str(ts or fallback_date or "").strip()
    if len(raw) >= 19 and raw[4] == "-" and raw[7] == "-":
        return f"{raw[8:10]}/{raw[5:7]}/{raw[0:4]} {raw[11:19]}"
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return f"{raw[8:10]}/{raw[5:7]}/{raw[0:4]}"
    return raw


@st.dialog(
    "Xem trước & Chọn giao dịch Bank Sync",
    width="large",
    icon=":material/fact_check:",
    on_dismiss=_dismiss_bank_preview_modal,
)
def _render_bank_sync_preview_modal(user: dict, theme_mode: str, lang: str) -> None:
    """Step 2 Interactive Preview Modal: Select/Deselect newly scanned or previously deleted bank transactions."""
    p = get_palette(theme_mode)
    preview_data = st.session_state.get("bank_sync_preview") or {}
    candidates: list[dict] = list(preview_data.get("candidates") or [])
    scanned_n = int(preview_data.get("scanned") or 0)
    skipped_active = int(preview_data.get("skipped_active") or 0)
    lookback_days = int(preview_data.get("lookback_days") or 7)
    batch_id = int(st.session_state.get("bank_preview_batch_id", 0))

    # Summary strip
    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;
                    padding:10px 14px;border-radius:10px;border:1px solid {p['border']};
                    background:{p['surface_alt']};margin-bottom:12px;font-size:0.84rem;color:{p['ink']};">
            <div>
                <strong>{('Đã quét' if lang == 'vi' else 'Scanned')}:</strong> {scanned_n} email ({lookback_days} {('ngày' if lang == 'vi' else 'days')})
                &nbsp;·&nbsp;
                <strong>{('Đang có trên web (bỏ qua)' if lang == 'vi' else 'Active on web (skipped)')}:</strong> {skipped_active}
            </div>
            <div style="font-weight:700;color:{p['primary']};">
                {len(candidates)} {('giao dịch sẵn sàng thêm' if lang == 'vi' else 'ready to import')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not candidates:
        st.info(
            f"Tất cả giao dịch hợp lệ trong **{lookback_days} ngày** gần nhất đều đã có mặt trong dữ liệu hiện tại của bạn. "
            "Nếu giao dịch bạn muốn khôi phục cũ hơn, hãy chọn phạm vi quét **14 ngày** hoặc **30 ngày** rồi quét lại."
            if lang == "vi"
            else f"All bank transactions from the past **{lookback_days} days** are already active in your data. Increase the lookback window to scan older alerts."
        )
        if st.button("Đóng" if lang == "vi" else "Close", width="stretch", key=f"bs_empty_close_{batch_id}"):
            st.session_state["show_bank_preview_modal"] = False
            st.rerun()
        return

    # Ensure checkbox keys exist
    for idx in range(len(candidates)):
        chk_k = f"bs_chk_{batch_id}_{idx}"
        if chk_k not in st.session_state:
            st.session_state[chk_k] = True

    # Toolbar: Select All / Deselect All
    tb_c1, tb_c2, tb_c3 = st.columns([1.2, 1.35, 3.0], vertical_alignment="center")
    with tb_c1:
        st.button(
            "Chọn tất cả" if lang == "vi" else "Select All",
            icon=":material/select_all:",
            key=f"bs_sel_all_{batch_id}",
            width="stretch",
            on_click=_set_all_preview_checks,
            args=(batch_id, len(candidates), True),
        )
    with tb_c2:
        st.button(
            "Bỏ chọn tất cả" if lang == "vi" else "Deselect All",
            icon=":material/deselect:",
            key=f"bs_desel_all_{batch_id}",
            width="stretch",
            on_click=_set_all_preview_checks,
            args=(batch_id, len(candidates), False),
        )
    with tb_c3:
        st.caption(
            "Tích chọn các giao dịch bạn muốn đẩy vào bảng dữ liệu chính (bao gồm giao dịch mới và giao dịch bạn đã xóa trước đó)."
            if lang == "vi"
            else "Check the transactions you want to import into your active database."
        )

    # Column header bar
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:42px 1.25fr 0.72fr 1.0fr 2.0fr 0.88fr;gap:12px;
                    padding:8px 10px;border-radius:8px;background:{p['surface_alt']};
                    border:1px solid {p['border']};font-size:0.74rem;font-weight:700;
                    color:{p['muted']};text-transform:uppercase;letter-spacing:0.03em;margin:6px 0 4px 0;">
            <div></div>
            <div>{('Thời gian' if lang == 'vi' else 'Timestamp')}</div>
            <div>{('Loại' if lang == 'vi' else 'Type')}</div>
            <div style="text-align:right;padding-right:10px;">{('Số tiền' if lang == 'vi' else 'Amount')}</div>
            <div>{('Nội dung' if lang == 'vi' else 'Content / Memo')}</div>
            <div>{('Danh mục' if lang == 'vi' else 'Category')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Scrollable preview list with per-row checkbox
    list_box = st.container(height=360, border=True) if len(candidates) > 4 else st.container(border=True)
    selected_indices: list[int] = []
    with list_box:
        for idx, item in enumerate(candidates):
            chk_key = f"bs_chk_{batch_id}_{idx}"
            r_chk, r_ts, r_type, r_amt, r_memo, r_cat = st.columns(
                [0.42, 1.25, 0.72, 1.0, 2.0, 0.88],
                vertical_alignment="center",
            )
            with r_chk:
                checked = st.checkbox(
                    f"select_{idx}",
                    key=chk_key,
                    label_visibility="collapsed",
                )
            if checked:
                selected_indices.append(idx)

            is_inc = str(item.get("type", "")).lower() == "income"
            ts_disp = _fmt_preview_ts(str(item.get("tx_timestamp") or ""), str(item.get("date") or ""))
            bank_disp = str(item.get("bank_name") or "Bank")
            amt_val = float(item.get("amount") or 0)
            sgn = "+" if is_inc else "-"
            amt_col = p["success"] if is_inc else p["danger"]
            type_lbl = ("Thu" if lang == "vi" else "In") if is_inc else ("Chi" if lang == "vi" else "Out")
            type_bg = "rgba(16,185,129,0.14)" if is_inc else "rgba(239,68,68,0.14)"
            memo_txt = str(item.get("transfer_memo") or item.get("description") or "—").strip()
            meta_parts: list[str] = []
            if item.get("counterparty"):
                meta_parts.append(str(item["counterparty"]))
            if item.get("reference_code"):
                meta_parts.append(f"Ref: {item['reference_code']}")
            meta_sub = " · ".join(meta_parts)

            with r_ts:
                st.markdown(
                    f"<div style='font-size:0.80rem;font-weight:600;color:{p['ink']};line-height:1.25;'>{html.escape(ts_disp)}</div>"
                    f"<div style='font-size:0.71rem;color:{p['muted']};margin-top:2px;'>{html.escape(bank_disp)}</div>",
                    unsafe_allow_html=True,
                )
            with r_type:
                st.markdown(
                    f"<span style='display:inline-block;padding:2px 9px;border-radius:999px;font-size:0.74rem;"
                    f"font-weight:700;color:{amt_col};background:{type_bg};'>{sgn} {html.escape(type_lbl)}</span>",
                    unsafe_allow_html=True,
                )
            with r_amt:
                st.markdown(
                    f"<div class='ml-num' style='text-align:right;padding-right:10px;font-size:0.84rem;font-weight:700;color:{amt_col};'>"
                    f"{sgn}{html.escape(format_vnd(amt_val))}</div>",
                    unsafe_allow_html=True,
                )
            with r_memo:
                sub_html = (
                    f"<div style='font-size:0.71rem;color:{p['muted']};margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{html.escape(meta_sub)}</div>"
                    if meta_sub
                    else ""
                )
                st.markdown(
                    f"<div style='font-size:0.81rem;color:{p['ink']};font-weight:500;line-height:1.3;'>{html.escape(memo_txt)}</div>{sub_html}",
                    unsafe_allow_html=True,
                )
            with r_cat:
                cat_disp = cat_label(str(item.get("category") or "Other"), lang)
                st.markdown(
                    f"<span style='display:inline-block;padding:2px 8px;border-radius:7px;font-size:0.73rem;"
                    f"border:1px solid {p['border']};background:{p['surface_alt']};color:{p['ink_secondary']};'>"
                    f"{html.escape(cat_disp)}</span>",
                    unsafe_allow_html=True,
                )
            if idx < len(candidates) - 1:
                st.markdown(
                    f"<hr style='margin:5px 0;border:none;border-top:1px solid {p['border']};opacity:0.65;'/>",
                    unsafe_allow_html=True,
                )

    # Live selected totals summary
    sel_items = [candidates[i] for i in selected_indices]
    sel_inc = sum(float(it.get("amount") or 0) for it in sel_items if str(it.get("type", "")).lower() == "income")
    sel_exp = sum(float(it.get("amount") or 0) for it in sel_items if str(it.get("type", "")).lower() != "income")
    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;
                    padding:9px 12px;margin:8px 0 12px 0;border-radius:9px;border:1px solid {p['border']};
                    background:{p['surface_alt']};font-size:0.82rem;color:{p['ink']};">
            <div><strong>{('Đã chọn' if lang == 'vi' else 'Selected')}:</strong> {len(sel_items)} / {len(candidates)} {('giao dịch' if lang == 'vi' else 'transactions')}</div>
            <div class="ml-num">
                <span style="color:{p['success']};font-weight:700;">+{html.escape(format_vnd(sel_inc))}</span>
                &nbsp;|&nbsp;
                <span style="color:{p['danger']};font-weight:700;">-{html.escape(format_vnd(sel_exp))}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Footer actions
    f_c1, f_c2 = st.columns([2.2, 1.0])
    with f_c1:
        confirm_lbl = (
            f"Thêm {len(sel_items)} giao dịch vào dữ liệu"
            if lang == "vi"
            else f"Import {len(sel_items)} Selected Transaction(s)"
        )
        if st.button(
            confirm_lbl,
            type="primary",
            icon=":material/download_done:",
            width="stretch",
            disabled=(len(sel_items) == 0),
            key=f"bs_import_confirm_{batch_id}",
        ):
            imp_res = import_selected_bank_transactions(user_id=user["id"], selected_items=sel_items)
            remaining = [candidates[i] for i in range(len(candidates)) if i not in set(selected_indices)]
            if remaining:
                next_batch_id = batch_id + 1
                st.session_state["bank_preview_batch_id"] = next_batch_id
                preview_data["candidates"] = remaining
                preview_data["skipped_active"] = skipped_active + int(imp_res.get("inserted", 0))
                st.session_state["bank_sync_preview"] = preview_data
                for r_idx in range(len(remaining)):
                    st.session_state[f"bs_chk_{next_batch_id}_{r_idx}"] = True
            else:
                st.session_state.pop("bank_sync_preview", None)
            st.session_state["show_bank_preview_modal"] = False
            st.session_state["force_reload_db"] = True
            added_cnt = int(imp_res.get("inserted", 0))
            st.session_state["last_webhook_toast"] = (
                f"Đã thêm thành công **{added_cnt}** giao dịch đã chọn vào dữ liệu chính!"
                if lang == "vi"
                else f"Successfully imported **{added_cnt}** selected transaction(s)!"
            )
            st.rerun()
    with f_c2:
        if st.button(
            "Đóng" if lang == "vi" else "Close",
            icon=":material/close:",
            width="stretch",
            key=f"bs_cancel_modal_{batch_id}",
        ):
            st.session_state["show_bank_preview_modal"] = False
            st.rerun()


@st.dialog("Hồ sơ cá nhân & Bảo mật Webhook")
def open_profile_dialog(user: dict, lang: str = "vi") -> None:
    """Allow signed-in users to edit their personal details or rotate their webhook token."""
    st.caption(f"Google / Email: **{user['email']}**")
    occ_opts = OCCUPATION_OPTIONS.get(lang, OCCUPATION_OPTIONS["vi"])
    goal_opts = GOAL_OPTIONS.get(lang, GOAL_OPTIONS["vi"])

    cur_occ = user.get("occupation") or occ_opts[0]
    if cur_occ not in occ_opts:
        occ_opts = [cur_occ] + occ_opts
    cur_goal = user.get("financial_goal") or goal_opts[0]
    if cur_goal not in goal_opts:
        goal_opts = [cur_goal] + goal_opts

    with st.form("ml_edit_profile_form"):
        new_name = st.text_input(t("onboard_name_lbl", lang), value=user.get("full_name", ""))
        new_occ = st.selectbox(t("onboard_occ_lbl", lang), options=occ_opts, index=occ_opts.index(cur_occ))
        c1, c2 = st.columns(2)
        with c1:
            new_inc = st.number_input(
                t("onboard_inc_lbl", lang),
                min_value=0,
                max_value=500_000_000,
                value=int(user.get("monthly_income") or 10_000_000),
                step=500_000,
            )
        with c2:
            new_bud = st.number_input(
                t("onboard_bud_lbl", lang),
                min_value=500_000,
                max_value=300_000_000,
                value=int(user.get("monthly_budget") or 8_000_000),
                step=500_000,
            )
        new_goal = st.selectbox(t("onboard_goal_lbl", lang), options=goal_opts, index=goal_opts.index(cur_goal))
        cur_banks = [b for b in (user.get("preferred_banks") or []) if b in BANK_CHOICES]
        new_banks = st.multiselect(t("onboard_banks_lbl", lang), options=BANK_CHOICES, default=cur_banks)
        new_secret = st.text_input(
            "Webhook Secret Header (tùy chọn cho SePay/Casso)" if lang == "vi" else "Optional Webhook Secret Header (SePay/Casso)",
            value=user.get("webhook_secret", ""),
            placeholder="Để trống nếu không yêu cầu header secret",
        )
        saved = st.form_submit_button(
            "Lưu thay đổi hồ sơ" if lang == "vi" else "Save Profile Changes",
            type="primary",
            width="stretch",
        )

    if saved:
        updated, err = update_user_profile(
            user_id=user["id"],
            full_name=new_name,
            occupation=new_occ,
            monthly_income=float(new_inc),
            monthly_budget=float(new_bud),
            financial_goal=new_goal,
            preferred_banks=new_banks,
            webhook_secret=new_secret,
        )
        if err or updated is None:
            st.error(err)
        else:
            st.session_state["current_user"] = updated
            st.session_state["monthly_budget"] = int(updated["monthly_budget"])
            st.toast("Đã cập nhật hồ sơ cá nhân!" if lang == "vi" else "Profile updated!")
            st.rerun()

    st.divider()
    if st.button(
        "Đổi mã Webhook Token mới" if lang == "vi" else "Rotate Personal Webhook Token",
        icon=":material/key:",
        width="stretch",
    ):
        updated = regenerate_webhook_token(user["id"])
        if updated:
            st.session_state["current_user"] = updated
            st.toast("Đã tạo Webhook Token mới!" if lang == "vi" else "Webhook token rotated!")
            st.rerun()


def render_top_header(user: dict | None, theme_mode: str, lang: str) -> None:
    """Render Row 1: Deep Navy Global Header Bar (Crisp white icons + Dynamic per-user profile chip)."""
    with st.container():
        st.markdown('<div class="ml-topbar-marker"></div>', unsafe_allow_html=True)

        if user is None:
            c_brand, c_spacer, c_lang, c_theme = st.columns(
                [2.6, 5.2, 0.9, 1.05], vertical_alignment="center"
            )
        elif not user.get("onboarding_completed", False):
            c_brand, c_spacer, c_lang, c_theme, c_logout = st.columns(
                [2.6, 2.7, 1.05, 1.2, 1.55], vertical_alignment="center"
            )
        else:
            c_brand, c_spacer, c_lang, c_theme, c_user, c_prof, c_logout = st.columns(
                [2.2, 1.8, 0.78, 0.95, 2.25, 0.92, 1.1], vertical_alignment="center"
            )

        with c_brand:
            st.markdown(
                f"""
                <div class="ml-top-brand">
                    {brand_logo_svg(28)}
                    <span class="ml-top-brand-name">MoneyLens AI</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_lang:
            next_lang_label = "EN" if lang == "vi" else "VI"
            if st.button(next_lang_label, icon=":material/translate:", key="btn_toggle_lang", width="stretch"):
                st.session_state["lang"] = "en" if lang == "vi" else "vi"
                st.rerun()

        with c_theme:
            theme_lbl = "Dark" if theme_mode == "light" else "Light"
            theme_ic = ":material/dark_mode:" if theme_mode == "light" else ":material/light_mode:"
            if st.button(theme_lbl, icon=theme_ic, key="btn_toggle_theme", width="stretch"):
                st.session_state["theme_mode"] = "dark" if theme_mode == "light" else "light"
                st.rerun()

        if user is not None and user.get("onboarding_completed", False):
            with c_user:
                display_name = user["full_name"] or user["email"]
                badge_lbl = user.get("occupation") or user.get("plan") or "Personal"
                initials = _initials_for(display_name, user["email"])
                grad = _avatar_gradient_for(user["email"])
                avatar_html = (
                    f'<img src="{html.escape(user["avatar_url"])}" alt="avatar"/>'
                    if user.get("avatar_url")
                    else html.escape(initials)
                )
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:flex-end;align-items:center;">
                        <div class="ml-user-chip" title="{html.escape(user['email'])}">
                            <div class="ml-avatar-circle" style="background:{grad};">{avatar_html}</div>
                            <div style="line-height:1.18;min-width:0;">
                                <div style="font-size:0.80rem;font-weight:600;color:#F8FAFC;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:165px;">
                                    {html.escape(display_name)}
                                </div>
                                <span class="ml-pro-tag">{html.escape(badge_lbl[:22])}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c_prof:
                if st.button(t("edit_profile", lang), icon=":material/manage_accounts:", key="btn_edit_profile", width="stretch"):
                    st.session_state["show_bank_preview_modal"] = False
                    open_profile_dialog(user, lang)

        if user is not None:
            with c_logout:
                if st.button(t("logout", lang), icon=":material/logout:", key="btn_logout", width="stretch"):
                    _sign_out_user()
                    st.rerun()


def render_google_signin_screen(theme_mode: str, lang: str) -> None:
    """Render full-page modern Google Sign-In Gate (zero hardcoded demo persona!)."""
    p = get_palette(theme_mode)
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    _, col_hero, col_card, _ = st.columns([0.06, 1.08, 0.96, 0.06], gap="large", vertical_alignment="top")

    with col_hero:
        hero_badge = (
            "Personal Finance Intelligence · 100% Legal Bank Auto-Sync"
            if lang == "en"
            else "Trợ lý Tài chính AI · Tự động đồng bộ ngân hàng hợp pháp 100%"
        )
        hero_h1 = (
            "Your money, understood.<br/>Your future, predicted."
            if lang == "en"
            else "Hiểu trọn dòng tiền.<br/>Dự đoán tương lai tài chính."
        )
        hero_p = (
            "Sign in with your own Google account to create a private workspace with your own display name, personalized budget, live Casso/SePay/PayOS/Forwarding auto-sync, and AI Advisor."
            if lang == "en"
            else "Đăng nhập bằng tài khoản Google của riêng bạn để sở hữu không gian tài chính độc lập: tên hiển thị riêng, thiết lập hồ sơ cá nhân lần đầu, tự động nhận giao dịch qua Webhook chỉ-đọc và trợ lý AI."
        )
        f1_t = "100% Legal Real-Time Bank Auto-Sync" if lang == "en" else "Tự động cập nhật khi có giao dịch (Hợp pháp 100%)"
        f1_d = (
            "Connect SePay, Casso, PayOS read-only webhooks or SMS/Email/Notification Forwarding (iOS Shortcuts, MacroDroid, Gmail) — zero bank passwords."
            if lang == "en"
            else "Tích hợp sẵn cổng Webhook chỉ-đọc Casso / SePay / PayOS và chuyển tiếp thông báo SMS/Email/App điện thoại — tuyệt đối không lưu mật khẩu ngân hàng."
        )
        f2_t = "3-Second Offline Capture & Bill Photo OCR" if lang == "en" else 'Nhập nhanh "Xăng 100k" & Quét ảnh hóa đơn AI'
        f2_d = (
            "No CSV needed. Type short notes or photograph receipts; Scikit-learn ML (92.6% CV) + Gemini 2.5 Flash Vision classify everything automatically."
            if lang == "en"
            else "Không cần file CSV. Gõ text ngắn hoặc chụp ảnh bill, Scikit-learn ML (92.6% CV) & Gemini Vision tự động bóc tách và phân loại 6 danh mục."
        )
        f3_t = "30-Day Cash Flow Forecast & Personal AI Advisor" if lang == "en" else "Dự báo 30 ngày & Trợ lý AI cá nhân hóa theo hồ sơ"
        f3_d = (
            "Statsmodels forecasting, What-If big purchase simulator (15M laptop), anomaly & subscription alerts customized to your personal budget."
            if lang == "en"
            else "Dự báo số dư Statsmodels, mô phỏng mua sắm What-If, phát hiện chi bất thường và gói đăng ký định kỳ theo đúng hạn mức ngân sách của bạn."
        )
        hero_html = (
            f'<div style="padding:12px 6px;">'
            f'<div style="display:inline-flex;align-items:center;gap:8px;padding:4px 12px;border-radius:999px;background:{p["primary_soft"]};border:1px solid {p["primary_border"]};color:{p["primary"]};font-size:0.78rem;font-weight:700;margin-bottom:14px;">'
            f'<span class="ml-live-dot"></span>{hero_badge}</div>'
            f'<h1 style="font-size:2.15rem;font-weight:700;line-height:1.2;letter-spacing:-0.03em;margin:0 0 12px 0;color:{p["ink"]};">{hero_h1}</h1>'
            f'<p style="font-size:0.96rem;color:{p["muted"]};line-height:1.6;margin-bottom:20px;">{hero_p}</p>'
            f'<div class="ml-feature-row"><div class="ml-kpi-icon" style="background:{p["success_soft"]};">{icon_svg("shield_check", color=p["success"], size=17)}</div>'
            f'<div><div style="font-weight:700;font-size:0.9rem;color:{p["ink"]};">{f1_t}</div>'
            f'<div style="font-size:0.81rem;color:{p["muted"]};margin-top:2px;">{f1_d}</div></div></div>'
            f'<div class="ml-feature-row"><div class="ml-kpi-icon" style="background:{p["primary_soft"]};">{icon_svg("zap", color=p["primary"], size=17)}</div>'
            f'<div><div style="font-weight:700;font-size:0.9rem;color:{p["ink"]};">{f2_t}</div>'
            f'<div style="font-size:0.81rem;color:{p["muted"]};margin-top:2px;">{f2_d}</div></div></div>'
            f'<div class="ml-feature-row"><div class="ml-kpi-icon" style="background:{p["warning_soft"]};">{icon_svg("trending_up", color=p["warning"], size=17)}</div>'
            f'<div><div style="font-weight:700;font-size:0.9rem;color:{p["ink"]};">{f3_t}</div>'
            f'<div style="font-size:0.81rem;color:{p["muted"]};margin-top:2px;">{f3_d}</div></div></div>'
            f'</div>'
        )
        st.markdown(hero_html, unsafe_allow_html=True)

    with col_card:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <div style="width:42px;height:42px;border-radius:12px;background:#FFFFFF;border:1px solid #CBD5E1;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(15,23,42,0.08);">
                        {google_logo_svg(22)}
                    </div>
                    <div>
                        <div style="font-size:1.18rem;font-weight:700;color:{p['ink']};">{html.escape(t('auth_title', lang))}</div>
                        <div style="font-size:0.8rem;color:{p['muted']};">{html.escape(t('demo_hint', lang))}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Case A: Real Google OAuth 2.0 Redirect Button (if GOOGLE_CLIENT_ID & SECRET are configured in .env)
            if is_google_oauth_configured():
                if "oauth_state" not in st.session_state:
                    st.session_state["oauth_state"] = secrets.token_urlsafe(16)
                auth_url = get_google_oauth_url(st.session_state["oauth_state"])
                st.markdown(
                    f"""
                    <a class="ml-google-oauth-link" href="{html.escape(auth_url)}" target="_self">
                        {google_logo_svg(20)}
                        <span>{html.escape(t('google_oauth_btn', lang))}</span>
                    </a>
                    <div style="text-align:center;font-size:0.76rem;color:{p['muted']};margin:12px 0 8px 0;">
                        {'hoặc đăng nhập nhanh tài khoản Google trên máy local' if lang == 'vi' else 'or quick local Google account sign-in'}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Case B: Instant Google Account Sign-In (works immediately on localhost & lets user test multiple accounts!)
            with st.form("ml_google_quick_signin"):
                g_email = st.text_input(
                    t("google_email_label", lang),
                    placeholder=t("google_email_ph", lang),
                )
                g_sub = st.form_submit_button(
                    t("google_signin_btn", lang),
                    icon=":material/account_circle:",
                    type="primary",
                    width="stretch",
                )
            if g_sub:
                user, err = sign_in_with_google_profile(g_email)
                if err or user is None:
                    st.error(err)
                else:
                    _reset_session_for_user(user, lang)
                    if user["onboarding_completed"]:
                        st.toast(f"Chào mừng trở lại, {user['full_name']}!" if lang == "vi" else f"Welcome back, {user['full_name']}!")
                    else:
                        st.toast("Đăng nhập Google thành công! Hãy hoàn tất hồ sơ cá nhân." if lang == "vi" else "Signed in with Google! Please complete your profile.")
                    st.rerun()

            # Saved Google accounts picker (each displays its own real name!)
            saved_accounts = list_google_accounts()
            if saved_accounts:
                st.markdown(
                    f"<div style='font-size:0.8rem;font-weight:600;color:{p['muted']};margin:12px 0 6px 0;'>{html.escape(t('google_saved_title', lang))}</div>",
                    unsafe_allow_html=True,
                )
                for acc in saved_accounts[:4]:
                    lbl_name = acc["full_name"] or ("(Chưa thiết lập tên)" if lang == "vi" else "(Pending profile)")
                    if st.button(
                        f"{lbl_name}  ·  {acc['email']}",
                        icon=":material/person:",
                        key=f"pick_google_{acc['id']}",
                        width="stretch",
                    ):
                        _reset_session_for_user(acc, lang)
                        st.rerun()

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            # Secondary Email/Password option
            with st.expander(t("email_pw_expander", lang), icon=":material/mail:"):
                t_in, t_up = st.tabs([t("login_tab", lang), t("register_tab", lang)])
                with t_in:
                    with st.form("ml_email_login_form"):
                        em_in = st.text_input(t("email_label", lang), placeholder="ban@gmail.com")
                        pw_in = st.text_input(t("password_label", lang), type="password", placeholder="••••••••")
                        sub_in = st.form_submit_button(t("login_btn", lang), type="primary", width="stretch")
                    if sub_in:
                        u, err = authenticate_user(em_in, pw_in)
                        if err or u is None:
                            st.error(err)
                        else:
                            _reset_session_for_user(u, lang)
                            st.rerun()
                with t_up:
                    with st.form("ml_email_reg_form"):
                        em_up = st.text_input(t("email_label", lang), placeholder="ban@gmail.com")
                        pw_up = st.text_input(t("password_label", lang), type="password", placeholder="Tối thiểu 6 ký tự")
                        sub_up = st.form_submit_button(t("register_btn", lang), type="primary", width="stretch")
                    if sub_up:
                        u, err = register_user("", em_up, pw_up, seed_sample_data=False)
                        if err or u is None:
                            st.error(err)
                        else:
                            _reset_session_for_user(u, lang)
                            st.rerun()

            if not is_google_oauth_configured():
                with st.expander(
                    "Bật Google OAuth 2.0 thật (Google Cloud Console)" if lang == "vi" else "Enable Live Google OAuth 2.0",
                    icon=":material/settings:",
                ):
                    st.caption(
                        "Hệ thống đã lập trình sẵn luồng Google OAuth 2.0 (`exchange_google_oauth_code`). "
                        "Khi deploy public, chỉ cần dán `GOOGLE_CLIENT_ID` và `GOOGLE_CLIENT_SECRET` vào file `.env` "
                        "với Redirect URI `http://localhost:8501` là nút đăng nhập Google thật sẽ tự động kích hoạt!"
                        if lang == "vi"
                        else "Full Google OAuth 2.0 authorization code flow is built in. Paste `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` into `.env` (Redirect URI: `http://localhost:8501`) to activate Google Cloud OAuth."
                    )


def render_onboarding_screen(user: dict, theme_mode: str, lang: str) -> None:
    """Mandatory first-time personal onboarding asking Full Name & financial profile before entering dashboard."""
    p = get_palette(theme_mode)
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    _, center, _ = st.columns([0.18, 0.64, 0.18])
    with center:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
                    <span class="ml-pill ml-pill-success">
                        {google_logo_svg(14)}
                        <span>{'Đã kết nối Google:' if lang == 'vi' else 'Connected Google:'} <strong>{html.escape(user['email'])}</strong></span>
                    </span>
                    <span class="ml-pill ml-pill-primary">{'Bước 1 / 1 · Thiết lập hồ sơ cá nhân' if lang == 'vi' else 'Step 1 / 1 · Personal Profile Setup'}</span>
                </div>
                <h2 style="margin:4px 0 6px 0;font-size:1.55rem;font-weight:700;color:{p['ink']};">
                    {html.escape(t('onboard_title', lang))}
                </h2>
                <p style="font-size:0.88rem;color:{p['muted']};margin:0 0 16px 0;line-height:1.5;">
                    {html.escape(t('onboard_sub', lang))}
                </p>
                """,
                unsafe_allow_html=True,
            )

            occ_opts = OCCUPATION_OPTIONS.get(lang, OCCUPATION_OPTIONS["vi"])
            goal_opts = GOAL_OPTIONS.get(lang, GOAL_OPTIONS["vi"])

            with st.form("ml_onboarding_form"):
                full_name = st.text_input(
                    t("onboard_name_lbl", lang),
                    value=user.get("full_name", ""),
                    placeholder=t("onboard_name_ph", lang),
                )
                occupation = st.selectbox(t("onboard_occ_lbl", lang), options=occ_opts, index=0)

                c1, c2 = st.columns(2)
                with c1:
                    monthly_income = st.number_input(
                        t("onboard_inc_lbl", lang),
                        min_value=0,
                        max_value=500_000_000,
                        value=10_000_000,
                        step=500_000,
                    )
                with c2:
                    monthly_budget = st.number_input(
                        t("onboard_bud_lbl", lang),
                        min_value=500_000,
                        max_value=300_000_000,
                        value=8_000_000,
                        step=500_000,
                    )

                financial_goal = st.selectbox(t("onboard_goal_lbl", lang), options=goal_opts, index=0)
                preferred_banks = st.multiselect(
                    t("onboard_banks_lbl", lang),
                    options=BANK_CHOICES,
                    default=["MBBank", "MoMo"],
                )
                st.caption(
                    "Tài khoản mới bắt đầu trắng tinh (0 giao dịch). Dữ liệu chỉ được lưu khi bạn tự nhập, chụp hóa đơn, thêm khoản cố định hoặc bật quét Email ngân hàng."
                    if lang == "vi"
                    else "New accounts start completely blank (0 transactions). Data is saved only when you add entries, scan receipts, add fixed bills, or enable Bank Email Sync."
                )

                confirm_btn = st.form_submit_button(
                    t("onboard_confirm_btn", lang),
                    icon=":material/check_circle:",
                    type="primary",
                    width="stretch",
                )

            if confirm_btn:
                updated, err = complete_user_onboarding(
                    user_id=user["id"],
                    full_name=full_name,
                    occupation=occupation,
                    monthly_income=float(monthly_income),
                    monthly_budget=float(monthly_budget),
                    financial_goal=financial_goal,
                    preferred_banks=preferred_banks,
                    seed_sample_data=False,
                )
                if err or updated is None:
                    st.error(err)
                else:
                    _reset_session_for_user(updated, lang)
                    st.toast(
                        f"Xin chào {updated['full_name']}! Không gian MoneyLens AI của bạn đã sẵn sàng."
                        if lang == "vi"
                        else f"Welcome {updated['full_name']}! Your MoneyLens AI workspace is ready."
                    )
                    st.rerun()


def render_sub_navigation(
    active_page: str,
    total_tx: int,
    selected_month: str,
    has_gemini: bool,
    webhook_ok: bool,
    theme_mode: str,
    lang: str,
) -> None:
    """Render Row 2: Horizontal 4-Screen Sub-Navigation Bar matching the reference screenshot."""
    p = get_palette(theme_mode)
    with st.container():
        st.markdown('<div class="ml-subnav-marker"></div>', unsafe_allow_html=True)
        nav_cols = st.columns([1.28, 1.15, 1.12, 1.15, 0.08, 1.25, 1.52, 1.45], vertical_alignment="center")

        nav_defs = [
            ("overview", t("nav_overview", lang), ":material/dashboard:"),
            ("spending", t("nav_spending", lang), ":material/trending_up:"),
            ("forecast", t("nav_forecast", lang), ":material/query_stats:"),
            ("advisor", t("nav_advisor", lang), ":material/auto_awesome:"),
        ]
        for idx, (key, label, ic) in enumerate(nav_defs):
            with nav_cols[idx]:
                btn_type = "primary" if active_page == key else "tertiary"
                if st.button(label, icon=ic, key=f"subnav_{key}", type=btn_type, width="stretch"):
                    st.session_state["active_page"] = key
                    st.rerun()

        with nav_cols[5]:
            mo_short = selected_month.replace("-", "/") if selected_month != "ALL" else "ALL"
            st.markdown(
                f"""
                <div style="text-align:right;font-size:0.78rem;line-height:1.25;color:{p['ink_secondary']};">
                    <div style="font-weight:600;color:{p['ink']};">SQLite Live</div>
                    <div style="color:{p['muted']};">({total_tx} {t('tx_short', lang)} · {html.escape(mo_short)})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with nav_cols[6]:
            if webhook_ok:
                pill_lbl = f"Auto-Sync :{get_webhook_port()}" if not has_gemini else f"Gemini + Sync :{get_webhook_port()}"
                pill_cls = "ml-pill-success"
                dot_color = p["success"]
            else:
                pill_lbl = t("gemini_active", lang) if has_gemini else t("grounded_ready", lang)
                pill_cls = "ml-pill-primary"
                dot_color = p["primary"]
            st.markdown(
                f"""
                <div style="display:flex;justify-content:center;">
                    <span class="ml-pill {pill_cls}">
                        <span style="width:7px;height:7px;border-radius:50%;background:{dot_color};display:inline-block;"></span>
                        {html.escape(pill_lbl)}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with nav_cols[7]:
            if st.button(t("refresh_data", lang), icon=":material/refresh:", key="subnav_refresh", width="stretch"):
                st.session_state["force_reload_db"] = True
                st.toast("Đã đồng bộ dữ liệu mới nhất từ SQLite!" if lang == "vi" else "Data synced from SQLite!")
                st.rerun()


def render_left_workspace_panel(
    user: dict,
    df: pd.DataFrame,
    avail_months: list[str],
    selected_month: str,
    monthly_budget: int,
    theme_mode: str,
    lang: str,
) -> None:
    """Render Left Workspace Column:
    Card 1: AI Capture & Live Legal Bank Auto-Sync (Quick Text | Bill OCR | Auto-Sync Webhook & Forwarding)
    Card 2: Data History (Clickable Month List)
    Card 3: Monthly Budget Slider & Gemini API Key
    """
    p = get_palette(theme_mode)
    api_key = str(st.session_state.get("gemini_api_key", "")).strip()

    # -----------------------------------------------------------------------
    # Card 1: AI Capture & Live Auto-Sync (NO CSV!)
    # -----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="ml-card-title">{icon_svg('zap', color=p['primary'], size=16)}<span>{html.escape(t('capture_title', lang))}</span></div>
            <div class="ml-card-caption">{html.escape(t('capture_sub', lang))}</div>
            """,
            unsafe_allow_html=True,
        )

        tab_quick, tab_bill, tab_bank = st.tabs(
            [t("tab_quick", lang), t("tab_bill", lang), t("tab_bank", lang)]
        )

        # ---- TAB A: Quick Text Offline Entry ("Xăng 100k") ----
        with tab_quick:
            with st.form("quick_text_capture_form", clear_on_submit=True):
                raw_quick = st.text_area(
                    "quick_input",
                    placeholder=t("quick_placeholder", lang),
                    height=94,
                    label_visibility="collapsed",
                )
                st.caption(t("quick_hint", lang))
                sub_quick = st.form_submit_button(
                    t("quick_btn", lang),
                    icon=":material/bolt:",
                    type="primary",
                    width="stretch",
                )

            if sub_quick and raw_quick.strip():
                parsed_list = parse_quick_text(raw_quick)
                if not parsed_list:
                    st.error(
                        "Không nhận diện được số tiền. Hãy nhập dạng: `Xăng 100k`, `Cà phê 45k`, `Lương 8.5tr`."
                        if lang == "vi"
                        else "Could not detect an amount. Try: `Gas 100k`, `Coffee 45k`, `Salary 8.5tr`."
                    )
                else:
                    for item in parsed_list:
                        insert_transaction(
                            user_id=user["id"],
                            date_str=item["date"],
                            description=item["description"],
                            amount=item["amount"],
                            tx_type=item["type"],
                            category=item["category"],
                            is_auto_categorized=True,
                            category_confidence=item["confidence"],
                            source_type="quick_text",
                            ai_note=item["ai_note"],
                        )
                    st.session_state["force_reload_db"] = True
                    st.session_state["last_capture_feedback"] = (
                        f"Đã lưu **{len(parsed_list)} giao dịch**: "
                        + " · ".join(
                            f"`{it['description']}` ({format_vnd(it['amount'])} → **{cat_label(it['category'], lang)}**)"
                            for it in parsed_list
                        )
                    )
                    st.rerun()

            if st.session_state.get("last_capture_feedback"):
                st.success(st.session_state.pop("last_capture_feedback"))

        # ---- TAB B: Bill / Bank Receipt / Handwritten Note Image OCR AI ----
        with tab_bill:
            st.caption(
                "Hỗ trợ đọc hóa đơn in, biên lai chuyển khoản ngân hàng & giấy viết tay (chữ viết tay)."
                if lang == "vi"
                else "Reads printed receipts, bank transfer screenshots, and handwritten bills/notes."
            )
            use_cam = st.toggle(t("bill_camera_toggle", lang), value=False, key="bill_cam_toggle")
            img_file = (
                st.camera_input(t("bill_upload_lbl", lang), key="bill_cam_input")
                if use_cam
                else st.file_uploader(
                    t("bill_upload_lbl", lang),
                    type=["png", "jpg", "jpeg", "webp"],
                    key="bill_file_upload",
                )
            )
            if img_file is not None:
                st.image(img_file, width="stretch")
                if st.button(t("bill_analyze_btn", lang), icon=":material/document_scanner:", type="primary", width="stretch"):
                    with st.spinner("AI đang đọc hóa đơn & chữ viết tay..." if lang == "vi" else "Scanning receipt & handwriting..."):
                        parsed_bill = parse_bill_image(
                            image_bytes=img_file.getvalue(),
                            filename=getattr(img_file, "name", "receipt.jpg"),
                            mime_type=getattr(img_file, "type", None) or "image/jpeg",
                            api_key=api_key,
                        )
                    st.session_state["pending_bill"] = parsed_bill

            pending_bill = st.session_state.get("pending_bill")
            if pending_bill:
                if pending_bill.get("used_vision_ai"):
                    st.success(pending_bill["ai_note"])
                else:
                    st.warning(pending_bill["ai_note"])
                with st.form("confirm_bill_form"):
                    b_desc = st.text_input("Mô tả / Cửa hàng" if lang == "vi" else "Merchant", value=pending_bill["description"])
                    b_amt = st.number_input("Số tiền (VND)" if lang == "vi" else "Amount (VND)", min_value=1000, value=int(pending_bill["amount"]), step=1000)
                    b_c1, b_c2 = st.columns(2)
                    with b_c1:
                        b_date = st.text_input("Ngày (YYYY-MM-DD)" if lang == "vi" else "Date", value=pending_bill.get("date", ""))
                    with b_c2:
                        b_type_opts = ["expense", "income"]
                        b_type = st.selectbox(
                            "Loại" if lang == "vi" else "Type",
                            options=b_type_opts,
                            index=0 if pending_bill.get("type", "expense") == "expense" else 1,
                            format_func=lambda x: t("expense_opt", lang) if x == "expense" else t("income_opt", lang),
                        )
                    all_bill_cats = EXPENSE_CATEGORIES + ["Income"]
                    cur_cat = pending_bill.get("category", "Other")
                    b_cat = st.selectbox(
                        "Danh mục" if lang == "vi" else "Category",
                        options=all_bill_cats,
                        index=all_bill_cats.index(cur_cat) if cur_cat in all_bill_cats else 5,
                        format_func=lambda c: cat_label(c, lang),
                    )
                    b_memo = st.text_area(
                        "Nội dung đọc được (Nội dung CK / Chữ viết tay)" if lang == "vi" else "Extracted Memo / Handwritten Text",
                        value=pending_bill.get("transfer_memo", ""),
                        height=76,
                    )
                    b_save = st.form_submit_button(t("bill_save_btn", lang), type="primary", width="stretch")
                if b_save:
                    final_cat = "Income" if b_type == "income" else (b_cat if b_cat != "Income" else "Other")
                    insert_transaction(
                        user_id=user["id"],
                        date_str=b_date.strip() or pending_bill["date"],
                        description=b_desc,
                        amount=float(b_amt),
                        tx_type=b_type,
                        category=final_cat,
                        is_auto_categorized=True,
                        category_confidence=pending_bill["confidence"],
                        source_type="bill_ocr",
                        transfer_memo=b_memo.strip(),
                        ai_note=pending_bill["ai_note"],
                    )
                    st.session_state.pop("pending_bill", None)
                    st.session_state["force_reload_db"] = True
                    st.toast("Đã lưu giao dịch từ ảnh hóa đơn!" if lang == "vi" else "Receipt saved!")
                    st.rerun()

        # ---- TAB C: Email Bank Sync (2-Step: Scan & Preview → Select & Import) + Optional Webhooks ----
        with tab_bank:
            email_cfg = get_email_sync_config(user["id"])
            email_connected = bool(email_cfg and email_cfg.get("email_address") and email_cfg.get("app_password_enc"))
            email_auto_push = bool(email_cfg and email_cfg.get("enabled"))
            badge_cls = "ml-pill-success" if email_connected else "ml-pill-neutral"
            dot_col = p["success"] if email_connected else p["muted"]
            if email_connected and email_auto_push:
                badge_txt = (
                    "Email Bank Sync · Đẩy tự động chạy nền"
                    if lang == "vi"
                    else "Email Bank Sync · Background Auto-Push"
                )
            elif email_connected:
                badge_txt = (
                    "Email Bank Sync · Đã kết nối (Xem trước)"
                    if lang == "vi"
                    else "Email Bank Sync · Connected (Preview Mode)"
                )
            else:
                badge_txt = "Email Bank Sync: Chưa kết nối" if lang == "vi" else "Email Bank Sync: Not connected"
            st.markdown(
                f'<div style="margin-bottom:8px;"><span class="ml-pill {badge_cls}">'
                f'<span class="ml-live-dot" style="background:{dot_col};"></span>{html.escape(badge_txt)}</span></div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Bước 1: Quét Email ngân hàng & lọc bỏ giao dịch đang có trên web → Bước 2: Xem trước, tích chọn & thêm vào dữ liệu."
                if lang == "vi"
                else "Step 1: Scan bank alert emails & filter out active web data → Step 2: Preview, select & import."
            )

            if email_connected:
                scan_days = st.selectbox(
                    "Phạm vi quét email" if lang == "vi" else "Scan lookback window",
                    options=[3, 7, 14, 30],
                    index=1,
                    format_func=lambda d: f"{d} ngày gần nhất" if lang == "vi" else f"Last {d} days",
                    key="bank_scan_lookback_days",
                )
                if st.button(
                    "Quét Email & Xem trước giao dịch" if lang == "vi" else "Scan & Preview Bank Transactions",
                    icon=":material/manage_search:",
                    type="primary",
                    key="btn_scan_email_now",
                    width="stretch",
                ):
                    with st.spinner("Đang quét hộp thư & đối chiếu dữ liệu đang có..." if lang == "vi" else "Scanning inbox against active data..."):
                        res_prev = preview_user_bank_emails(
                            user_id=user["id"],
                            api_key=api_key,
                            lookback_days=int(scan_days),
                        )
                    if res_prev.get("ok"):
                        _open_bank_preview_batch(res_prev)
                        st.rerun()
                    else:
                        st.error(res_prev.get("error", "Lỗi quét email"))

                pending_prev = st.session_state.get("bank_sync_preview") or {}
                pending_cands = pending_prev.get("candidates") or []
                if pending_cands and not st.session_state.get("show_bank_preview_modal"):
                    if st.button(
                        (
                            f"Mở lại danh sách xem trước ({len(pending_cands)} giao dịch)"
                            if lang == "vi"
                            else f"Reopen Preview List ({len(pending_cands)} pending)"
                        ),
                        icon=":material/fact_check:",
                        key="btn_reopen_bank_preview",
                        width="stretch",
                    ):
                        st.session_state["show_bank_preview_modal"] = True
                        st.rerun()

                if email_cfg.get("last_status"):
                    ts_chk = str(email_cfg.get("last_checked_at", ""))[11:16]
                    st.caption(f"Trạng thái ({ts_chk or 'vừa xong'}): {email_cfg['last_status']}")
                if email_cfg.get("last_error"):
                    st.warning(email_cfg["last_error"])

            if st.session_state.get("last_webhook_toast"):
                st.success(st.session_state.pop("last_webhook_toast"))

            with st.form("email_bank_sync_form"):
                em_addr = st.text_input(
                    "Email nhận biến động ngân hàng" if lang == "vi" else "Bank Alert Email",
                    value=(email_cfg["email_address"] if email_cfg and email_cfg.get("email_address") else user["email"]),
                    placeholder="tenban@gmail.com",
                )
                em_pw = st.text_input(
                    "Mật khẩu ứng dụng (App Password)" if lang == "vi" else "Email App Password (16 chars)",
                    type="password",
                    placeholder="xxxx xxxx xxxx xxxx" if not (email_cfg and email_cfg.get("app_password_enc")) else "Đã lưu (để trống nếu giữ nguyên)",
                )
                em_host = st.text_input(
                    "IMAP Host",
                    value=(email_cfg["imap_host"] if email_cfg and email_cfg.get("imap_host") else "imap.gmail.com"),
                )
                em_enable = st.toggle(
                    "Tự động đẩy thẳng khi có email mới (bỏ qua bước xem trước)"
                    if lang == "vi"
                    else "Background auto-push new emails (skip preview)",
                    value=email_auto_push if email_cfg else False,
                )
                save_em = st.form_submit_button(
                    "Lưu kết nối & Quét xem trước" if lang == "vi" else "Save Connection & Preview Scan",
                    icon=":material/mark_email_read:",
                    type="secondary" if email_connected else "primary",
                    width="stretch",
                )

            if save_em:
                with st.spinner("Đang kiểm tra kết nối IMAP..." if lang == "vi" else "Testing IMAP connection..."):
                    ok_em, msg_em = save_and_test_email_config(
                        user_id=user["id"],
                        email_address=em_addr,
                        raw_app_password=em_pw,
                        imap_host=em_host,
                        enabled=em_enable,
                    )
                if ok_em:
                    with st.spinner("Đang quét 7 ngày gần nhất để xem trước..." if lang == "vi" else "Scanning last 7 days for preview..."):
                        prev_res = preview_user_bank_emails(
                            user_id=user["id"],
                            api_key=api_key,
                            lookback_days=int(st.session_state.get("bank_scan_lookback_days", 7)),
                        )
                    if prev_res.get("ok"):
                        _open_bank_preview_batch(prev_res)
                    else:
                        st.session_state["last_webhook_toast"] = msg_em
                    st.rerun()
                else:
                    st.error(msg_em)

            with st.expander(
                "Hướng dẫn bật Email ngân hàng & lấy App Password (1 phút)" if lang == "vi" else "How to get Gmail App Password (1 min)",
                icon=":material/help_outline:",
            ):
                st.markdown(
                    "1. Trong app ngân hàng (**MBBank, VCB, Techcombank, ACB, TPBank, MoMo...**), bật mục **Nhận thông báo biến động số dư qua Email**.\n"
                    "2. Vào **[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)** (cần bật Xác minh 2 bước) → tạo App Password 16 ký tự tên `MoneyLens`.\n"
                    "3. Dán mã 16 ký tự vào ô phía trên và bấm **Lưu kết nối**. Mật khẩu được mã hóa AES/Fernet nội bộ, chỉ đọc email biến động (chế độ `readonly`), không bao giờ đụng mật khẩu ngân hàng!"
                    if lang == "vi"
                    else "1. Enable bank balance alert emails inside your banking app.\n2. Create a 16-char Google App Password at **myaccount.google.com/apppasswords**.\n3. Paste it above — encrypted locally with Fernet and opened in read-only IMAP mode."
                )

            # 1-Click Test Pipeline: Simulated Bank Email -> AI Extraction -> Preview & Select Modal
            with st.expander(
                "Thử luồng Email → AI bóc tách → Xem trước & Chọn" if lang == "vi" else "Test Email → AI Extract → Preview & Select",
                icon=":material/science:",
            ):
                sim_idx = st.selectbox(
                    "Chọn 1 email ngân hàng mẫu:" if lang == "vi" else "Choose a sample bank email:",
                    options=list(range(len(SAMPLE_BANK_EMAILS))),
                    format_func=lambda i: SAMPLE_BANK_EMAILS[i]["label"],
                    key="email_sim_picker",
                )
                if st.button(
                    "Quét thử Email mẫu (Xem trước)" if lang == "vi" else "Preview Sample Bank Email",
                    icon=":material/auto_awesome:",
                    key="btn_run_sim_email",
                    width="stretch",
                ):
                    with st.spinner("AI đang đọc email & bóc tách giao dịch..." if lang == "vi" else "AI extracting email..."):
                        sim_prev = simulate_bank_email_preview(user=user, sample_index=sim_idx, api_key=api_key)
                    if sim_prev.get("ok"):
                        _open_bank_preview_batch(sim_prev)
                        st.rerun()
                    else:
                        st.error(sim_prev.get("error", "Không bóc tách được email."))

            # Live Recent Sync Feed
            recent_ev = get_recent_webhook_events(user["id"], limit=3)
            if recent_ev:
                st.markdown(
                    f"<div style='font-size:0.78rem;font-weight:700;color:{p['ink_secondary']};margin:8px 0 4px 0;'>{html.escape(t('autosync_feed_title', lang))}</div>",
                    unsafe_allow_html=True,
                )
                for ev in recent_ev:
                    sgn = "+" if ev["tx_type"] == "income" else "-"
                    ts_short = str(ev["received_at"])[11:16]
                    st.markdown(
                        f'<div style="padding:7px 9px;border-radius:9px;border:1px solid {p["border"]};background:{p["surface_alt"]};margin-bottom:6px;font-size:0.75rem;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                        f'<span style="font-weight:700;color:{p["primary"]};">{html.escape(ev["provider"])}</span>'
                        f'<span class="ml-num" style="font-weight:700;color:{p["success"] if ev["tx_type"]=="income" else p["danger"]};">{sgn}{html.escape(format_vnd(ev["amount"]))}</span>'
                        f'</div>'
                        f'<div style="color:{p["muted"]};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px;">{ts_short} · {html.escape(ev["summary"])}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Optional Advanced Read-Only Webhooks (SePay / Casso / PayOS) kept cleanly collapsed
            with st.expander(
                "Kết nối nâng cao: Webhook SePay / Casso / PayOS" if lang == "vi" else "Advanced: SePay / Casso / PayOS Webhook",
                icon=":material/webhook:",
            ):
                wh_base = get_webhook_base_url()
                user_tok = user.get("webhook_token", "")
                channel_map = {
                    "sepay": "SePay.vn (Webhook chỉ-đọc)",
                    "casso": "Casso.vn (Webhook chỉ-đọc)",
                    "payos": "PayOS (Webhook chỉ-đọc)",
                    "forward": "iOS Shortcut / MacroDroid Forwarding",
                }
                chosen_ch = st.selectbox(
                    "Kênh Webhook:",
                    options=list(channel_map.keys()),
                    format_func=lambda k: channel_map[k],
                    key="bank_autosync_channel",
                )
                st.code(f"{wh_base}/api/webhook/{chosen_ch}/{user_tok}", language="text")
                if st.button(t("autosync_test_btn", lang), icon=":material/sync:", key="btn_trigger_live_webhook", width="stretch"):
                    ok_hit, res_data = send_live_test_webhook(
                        provider=chosen_ch,
                        webhook_token=user_tok,
                        secret=user.get("webhook_secret", ""),
                    )
                    if ok_hit and res_data.get("ok"):
                        st.session_state["force_reload_db"] = True
                        st.session_state["last_webhook_toast"] = f"Webhook **{res_data.get('provider')}** đã đẩy giao dịch mới vào SQLite!"
                        st.rerun()
                    else:
                        st.error(f"Webhook lỗi: {res_data.get('error', 'Unknown error')}")

            # Manual paste fallback inside clean expander
            with st.expander(t("autosync_manual_exp", lang), icon=":material/content_paste:"):
                sample_choice = st.selectbox(
                    t("bank_sample_lbl", lang),
                    options=["-- Chọn mẫu thử nhanh --"] + [s["label"] for s in SAMPLE_BANK_NOTIFICATIONS],
                    key="bank_sample_picker",
                )
                default_alert = ""
                if sample_choice != "-- Chọn mẫu thử nhanh --":
                    for s in SAMPLE_BANK_NOTIFICATIONS:
                        if s["label"] == sample_choice:
                            default_alert = s["text"]
                            break

                raw_alert = st.text_area(
                    "bank_alert_input",
                    value=default_alert,
                    placeholder=t("bank_placeholder", lang),
                    height=84,
                    label_visibility="collapsed",
                )
                if st.button(t("bank_analyze_btn", lang), icon=":material/account_balance:", width="stretch"):
                    if not raw_alert.strip():
                        st.warning("Hãy dán tin nhắn biến động hoặc chọn 1 mẫu phía trên.")
                    else:
                        parsed_bank = parse_bank_notification(
                            raw_alert,
                            monthly_budget=float(monthly_budget),
                            api_key=api_key,
                        )
                        if parsed_bank is None:
                            st.error("Không tìm thấy số tiền trong thông báo chuyển khoản.")
                        else:
                            st.session_state["pending_bank"] = parsed_bank

                pending_bank = st.session_state.get("pending_bank")
                if pending_bank:
                    sign = "+" if pending_bank["type"] == "income" else "-"
                    st.markdown(
                        f'<div class="ml-ai-banner" style="margin:8px 0;padding:10px 12px;">'
                        f'<div class="ml-ai-banner-title">{icon_svg("sparkles", color=p["primary"], size=14)} {html.escape(pending_bank["bank_name"])} · {sign}{html.escape(format_vnd(pending_bank["amount"]))}</div>'
                        f'<div class="ml-ai-banner-body" style="font-size:0.79rem;"><strong>Danh mục:</strong> {html.escape(cat_label(pending_bank["category"], lang))}<br/><strong>Nội dung CK:</strong> {html.escape(pending_bank["transfer_memo"])}<br/>{pending_bank["ai_note"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(t("bank_save_btn", lang), icon=":material/check_circle:", type="primary", width="stretch"):
                        insert_transaction(
                            user_id=user["id"],
                            date_str=pending_bank["date"],
                            description=pending_bank["description"],
                            amount=pending_bank["amount"],
                            tx_type=pending_bank["type"],
                            category=pending_bank["category"],
                            is_auto_categorized=True,
                            category_confidence=pending_bank["confidence"],
                            source_type="bank_sync",
                            transfer_memo=pending_bank["transfer_memo"],
                            ai_note=pending_bank["ai_note"],
                        )
                        st.session_state.pop("pending_bank", None)
                        st.session_state["force_reload_db"] = True
                        st.toast("Đã lưu giao dịch & phân tích nội dung chuyển khoản!")
                        st.rerun()

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Card 2: Data History (Clickable Vertical Month List)
    # -----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown(
            f'<div class="ml-card-title">{icon_svg("calendar", color=p["primary"], size=16)}<span>{html.escape(t("history_title", lang))}</span></div>',
            unsafe_allow_html=True,
        )
        month_choices = avail_months + ["ALL"]
        latest_m = avail_months[0] if avail_months else None
        for m_val in month_choices:
            lbl = fmt_month_label(m_val, lang=lang, is_latest=(m_val == latest_m))
            is_sel = m_val == selected_month
            if st.button(
                lbl,
                key=f"hist_m_{m_val}",
                type="primary" if is_sel else "tertiary",
                width="stretch",
            ):
                st.session_state["selected_month"] = m_val
                st.rerun()

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Card 3: Budget Slider & Persisted AI API Key (Gemini / OpenAI / Groq)
    # -----------------------------------------------------------------------
    with st.container(border=True):
        st.markdown(
            f'<div class="ml-card-title">{icon_svg("target", color=p["primary"], size=16)}<span>{html.escape(t("budget_title", lang))}</span></div>',
            unsafe_allow_html=True,
        )
        slider_min = 1_000_000
        slider_max = max(30_000_000, int(monthly_budget) + 5_000_000)
        clamped_budget = min(max(int(monthly_budget), slider_min), slider_max)
        new_budget = st.slider(
            t("budget_slider", lang),
            min_value=slider_min,
            max_value=slider_max,
            value=clamped_budget,
            step=500_000,
            format="%d ₫",
            key="left_budget_slider",
        )
        if new_budget != int(monthly_budget):
            st.session_state["monthly_budget"] = int(new_budget)
            user["monthly_budget"] = float(new_budget)
            update_user_budget(user["id"], float(new_budget))

        with st.expander("AI API Key (Gemini / OpenAI / Groq)", icon=":material/key:"):
            st.caption(
                "Hỗ trợ mọi loại khóa: Google (`AQ....` hoặc `AIza...`), OpenAI (`sk-...`), Groq (`gsk_...`) — tự động lưu và bật OCR đọc hóa đơn in, biên lai ngân hàng & chữ viết tay."
                if lang == "vi"
                else "Accepts any key: Google (`AQ....` or `AIza...`), OpenAI (`sk-...`), Groq (`gsk_...`) — persisted automatically for unlimited AI chat & receipt/handwriting OCR."
            )
            k_in = st.text_input(
                "API Key",
                value=st.session_state.get("gemini_api_key", ""),
                type="password",
                placeholder="AQ.... / AIza... / sk-... / gsk_...",
            )
            k_clean = k_in.strip()
            if k_clean != st.session_state.get("gemini_api_key", ""):
                st.session_state["gemini_api_key"] = k_clean
                set_app_setting("ai_api_key", k_clean)

    # Render Bank Sync Step-2 Preview & Select Modal when triggered
    if st.session_state.get("show_bank_preview_modal"):
        _render_bank_sync_preview_modal(user=user, theme_mode=theme_mode, lang=lang)
