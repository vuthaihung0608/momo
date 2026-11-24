# 09. Tư vấn Pháp lý & Kiến trúc Kết nối Giao dịch Ngân hàng tại Việt Nam — MoneyLens AI

> Tài liệu hướng dẫn kỹ thuật & tuân thủ pháp lý dành cho đội ngũ MoneyLens AI khi đưa sản phẩm từ MVP sang vận hành thực tế tại Việt Nam.

---

## 1. Lấy API ngân hàng có phạm pháp không?

Câu trả lời phụ thuộc hoàn toàn vào **cách bạn lấy dữ liệu**:

| Hình thức | Tính pháp lý & Rủi ro | Khuyến nghị |
|---|---|---|
| **Tự cào (scrape) / reverse-engineer API nội bộ** của app ngân hàng, hoặc yêu cầu người dùng nhập mật khẩu Internet Banking / OTP | ❌ **Rủi ro pháp lý rất cao:** Vi phạm điều khoản dịch vụ ngân hàng, tiềm ẩn vi phạm **Nghị định 13/2023/NĐ-CP** (Bảo vệ dữ liệu cá nhân) & quy định an toàn hệ thống thông tin của NHNN | **TUYỆT ĐỐI KHÔNG LÀM** |
| **Người dùng chủ động chuyển tiếp thông báo biến động số dư** (SMS / Email / Push Notification) vào tài khoản của chính họ | ✅ **Hợp pháp 100%:** Dữ liệu do chủ tài khoản tự chia sẻ có chủ đích (*explicit consent*), ứng dụng **không bao giờ** giữ mật khẩu hay quyền chuyển tiền | **Dùng ngay cho bản vận hành cá nhân & cuộc thi** *(đã tích hợp sẵn trong tab Bank Sync!)* |
| **Cổng Webhook chỉ-đọc hợp pháp tại Việt Nam** (Casso.vn, SePay.vn, PayOS...) | ✅ **Hợp pháp & Phổ biến nhất cho Startup Việt:** Chạy theo cơ chế webhook đẩy biến động số dư (chỉ đọc) vào backend trong 3–5 giây | **Khuyên dùng khi vận hành thực tế quy mô vừa** |
| **Open API trực tiếp của ngân hàng theo Thông tư 64/2024/TT-NHNN** | ✅ **Chính thống cấp ngân hàng:** Hỗ trợ OAuth2 + consent chuẩn Open Banking (Vietcombank, Techcombank, MB, BIDV...) | **Dùng khi thành lập pháp nhân doanh nghiệp & mở rộng quy mô lớn** |

---

## 2. Lộ trình 3 giai đoạn tích hợp thực tế cho MoneyLens AI

### Giai đoạn 1 — Đã triển khai chạy thật ngay trong MoneyLens AI
1. **Bank Sync (Biến động số dư + AI phân tích nội dung chuyển khoản):**
   - Người dùng dán thông báo biến động từ **MBBank, Vietcombank, Techcombank, ACB, TPBank, VPBank, BIDV, MoMo, ZaloPay** (hoặc thiết lập **iOS Shortcuts / Android MacroDroid** tự động gửi thông báo ngân hàng qua webhook).
   - `src/capture.py` tự bóc tách: *Ngân hàng, Số tiền, Thu/Chi, Ngày, Nội dung chuyển khoản (memo)* → phân loại bằng mô hình Scikit-learn (92.6% CV) → **AI phân tích ngữ cảnh** (chia tiền nhóm, hóa đơn định kỳ, mua sắm TMĐT, cảnh báo giao dịch chiếm >25% ngân sách).
2. **Chi tiêu Offline không qua ngân hàng:**
   - **Nhập nhanh bằng text tự nhiên:** gõ `Xăng 100k`, `Highlands 45k`, `Nhận lương 8.5tr` (nhập 1 dòng hoặc nhiều dòng).
   - **Quét ảnh hóa đơn (Bill OCR AI):** chụp ảnh / tải ảnh biên lai để **Gemini 2.5 Flash Vision** đọc cửa hàng, ngày, tổng tiền & tự phân loại.

### Giai đoạn 2 — Tự động hóa 100% qua Webhook hợp pháp (Casso / SePay / PayOS)
Khi vận hành thực tế cho hàng trăm/nghìn người dùng:
1. Tạo 1 endpoint REST API nhỏ (FastAPI/Flask) dạng `POST /api/webhooks/bank-sync` kèm xác thực chữ ký HMAC secret token.
2. Kết nối tài khoản **SePay.vn** hoặc **Casso.vn** (hỗ trợ đa số ngân hàng lớn tại VN).
3. Mỗi khi có biến động số dư, webhook gửi JSON `{ amount, description, when, subAccount }` → backend gọi trực tiếp `parse_bank_notification()` và `insert_transaction()` vào SQLite/PostgreSQL.

### Giai đoạn 3 — Open Banking chính thức (Thông tư 64/2024/TT-NHNN)
- Đăng ký đối tác TPP (Third-Party Provider) trên Developer Portal của ngân hàng theo chuẩn OAuth 2.0 / OpenAPI của NHNN.
- Luôn tuân thủ Nghị định 13/2023/NĐ-CP: có trang Chính sách bảo mật, cơ chế xóa toàn bộ dữ liệu tài khoản theo yêu cầu người dùng và mã hóa dữ liệu nhạy cảm.
