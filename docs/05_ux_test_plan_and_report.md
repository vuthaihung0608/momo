# 05. Kế hoạch & Báo cáo Kiểm thử Trải nghiệm Người dùng (UX Test Plan & QA Report) — MoneyLens AI

> **Phụ trách:** Member 1 — Product & Frontend (`Product Owner`)  
> **Ngày thực hiện kiểm thử:** 21/11/2026  
> **Phạm vi:** Toàn bộ 4 màn hình Streamlit (`app.py`, `pages/overview.py`, `pages/spending.py`, `pages/forecast.py`, `pages/advisor.py`), bộ xử lý CSV chuẩn 5 cột, kiểm thử biên & đánh giá trải nghiệm người dùng (Nielsen's Usability Heuristics).

---

## 1. Bảng kết quả Kiểm thử Chức năng & Kịch bản Biên (15 Test Cases)

| ID | Màn hình / Thành phần | Kịch bản kiểm thử | Kết quả mong đợi | Kết quả thực tế | Trạng thái |
|---|---|---|---|---|---|
| **TC-01** | `app.py` (Khởi động) | Mở ứng dụng lần đầu chưa tải file CSV | Tự động nạp dữ liệu mẫu sinh viên 3 tháng (94 dòng), giao diện hiển thị ngay không bị màn hình trắng | Nạp thành công 94 giao dịch, không lỗi | ✅ PASS |
| **TC-02** | CSV Validator | Tải file chuẩn 5 cột có 13 dòng trống cột `category` | Tự động phân loại 13 dòng vào 6 danh mục chuẩn và gắn nhãn `✨` trên bảng | Tự phân loại chính xác 13/13 dòng | ✅ PASS |
| **TC-03** | CSV Validator (Biên) | Tải file CSV thiếu cột (`date, amount`) | Hiển thị thông báo lỗi tiếng Việt rõ ràng, liệt kê cột bị thiếu, không crash app | Báo lỗi đúng danh sách cột thiếu, giữ nguyên dữ liệu cũ | ✅ PASS |
| **TC-04** | CSV Validator (Biên) | Tải file CSV có số tiền âm (`-45000`) & trống `category` | Tự chuẩn hóa `amount` sang số dương (`45000`), phân loại `Highlands Coffee` → `Food`, kèm thông báo | Chuẩn hóa thành `45000` & gán `Food` kèm thông báo | ✅ PASS |
| **TC-05** | Screen 1 — Overview | Chuyển chế độ biểu đồ `Số dư dòng tiền` ↔ `Thu vs Chi` | Biểu đồ cập nhật mượt, đúng đơn vị VND và đúng kỳ tháng đang chọn | Cả 2 biểu đồ render chuẩn xác, hover rõ VND | ✅ PASS |
| **TC-06** | Screen 1 — Overview | Tìm kiếm `"Highlands"`, lọc `Chi tiêu`, lọc danh mục `Ăn uống` | Bảng lọc đúng số dòng, hiển thị định dạng `-45.000 ₫` và dấu `✨` | Lọc tức thì, hiển thị rõ tổng dòng lọc được | ✅ PASS |
| **TC-07** | Screen 2 — Spending | Kiểm tra tỷ trọng 6 danh mục & phát hiện tăng đột biến MoM | Nổi bật `Mua sắm` chiếm `42.6%`, tăng `+281.2%` (cột đỏ) và `Ăn uống` tăng `+26.7%` | Hiển thị đúng cả Donut, bảng và AI Spike Banner | ✅ PASS |
| **TC-08** | Screen 2 — Spending | Kiểm tra phát hiện giao dịch bất thường (Anomaly) | Bắt đúng `Tai nghe Sony 2.650.000 ₫` (6.9x TB) & `Lẩu băng chuyền 460.000 ₫` (3.6x TB), không gắn nhầm Tiền trọ | Bắt chính xác 2 giao dịch đột biến thực sự | ✅ PASS |
| **TC-09** | Screen 2 — Spending | Kiểm tra phát hiện chi tiêu định kỳ & Subscriptions | Chỉ liệt kê đúng 7 khoản cố định/subscription (Phòng trọ, Điện nước, FPT, 4G, Netflix, Spotify, iCloud+) | Liệt kê chuẩn 7 khoản (`4.139.333 ₫/tháng`) sau fix QA-01 | ✅ PASS |
| **TC-10** | Screen 3 — Forecast | Kiểm tra biểu đồ dự báo 30 ngày & đường `Hôm nay` | Hiển thị liền mạch lịch sử + mốc `Hôm nay (21/11)` + dự báo cuối tháng (`8.960.585 ₫`) | Render đầy đủ khoảng tin cậy & giải thích xu hướng | ✅ PASS |
| **TC-11** | Screen 3 — Forecast | Nhấn Preset `💻 Mua Laptop` (15.000.000 ₫) | Cập nhật `scen_extra_cost = 15,000,000`, xuất hiện vùng ĐỎ âm (`-1.491.382 ₫`) & đường chấm so sánh gốc | Chuyển sang vùng đỏ cảnh báo ngay lập tức | ✅ PASS |
| **TC-12** | Screen 3 — Forecast | Nhấn Preset `🌱 Tiết kiệm` (cắt 20% Food, 35% Shopping, hủy Subs) | Cập nhật thanh trượt & công tắc, hiển thị hộp xanh số tiền tiết kiệm thêm sau 30 ngày | Cập nhật đồng bộ tất cả widget và biểu đồ | ✅ PASS |
| **TC-13** | Screen 4 — Advisor | Bấm nút gợi ý `"Nếu tháng sau tôi mua laptop 15 triệu thì sao?"` | Trả lời số dư trước/sau (`-1.491.382 ₫`), đề xuất trả góp 0% 6 tháng + nhúng biểu đồ so sánh | Phản hồi `< 0.3s`, bám sát 100% số liệu & có biểu đồ | ✅ PASS |
| **TC-14** | Screen 4 — Advisor | Nhập câu hỏi tự do `"Tôi tiêu nhiều nhất vào đâu?"` vào `chat_input` | Trả lời đúng `Mua sắm (42.6%)`, liệt kê giao dịch lớn nhất + biểu đồ thanh ngang | Hoạt động mượt, lưu lịch sử hội thoại đúng thứ tự | ✅ PASS |
| **TC-15** | Toàn bộ 4 trang | Chạy kiểm thử tự động `streamlit.testing.v1.AppTest` | 0 Python exception, 0 Pandas 3 Copy-on-Write error, 0 lỗi tương tác widget | **PASS 100%** trên `app.py` và cả 4 file trong `pages/` | ✅ PASS |

---

## 2. Nhật ký Lỗi UX phát hiện & Khắc phục trong quá trình QA (Bug Fix Log)

| Mã lỗi | Mô tả vấn đề phát hiện khi kiểm thử | Nguyên nhân | Cách khắc phục đã áp dụng | Trạng thái |
|---|---|---|---|---|
| **QA-01** | `Highlands Coffee` (45.000 ₫, nhóm `Food`) bị gắn nhầm vào danh sách *Chi tiêu định kỳ / Hóa đơn cố định* | Giao dịch cà phê xuất hiện đúng 1 lần/tháng ở đầu 3 tháng với tên giống hệt nhau | Bổ sung bộ lọc ngữ nghĩa trong `ui/service_adapter.py` (`detect_recurring_transactions`): loại trừ nhóm `Food` trừ khi có từ khóa gói dịch vụ (`subscription`, `gói`, `membership`...) | ✅ Đã sửa & kiểm thử lại |
| **QA-02** | Khởi động Streamlit ở môi trường offline/hạn chế mạng có thể chậm nhẹ do telemetry mặc định | `gatherUsageStats` mặc định bật trong Streamlit | Thêm `[browser] gatherUsageStats = false` vào `.streamlit/config.toml` giúp khởi động tức thì khi demo offline | ✅ Đã sửa |

---

## 3. Đánh giá Trải nghiệm theo Bộ Tiêu chí UX (Usability Heuristics)

- **Tính trực quan trạng thái hệ thống (Visibility of System Status):** Thanh sidebar luôn hiển thị nguồn CSV hiện hành, tổng số giao dịch, số dòng được tự phân loại và trạng thái kết nối backend `src/`.
- **Ngôn ngữ gần gũi người dùng Việt (Match Real World):** 100% nhãn giao diện dùng tiếng Việt tự nhiên, đơn vị tiền tệ chuẩn Việt Nam (`10.685.000 ₫`), tên cửa hàng quen thuộc (*Highlands, Shopee, TikTok Shop, MoMo, Viettel, FPT*).
- **Phòng ngừa & xử lý lỗi nhẹ nhàng (Error Prevention):** Tích hợp nút tải **Form CSV trống** & **CSV mẫu** ngay cạnh khung upload; file sai cột hoặc có số âm được giải thích rõ thay vì văng lỗi kỹ thuật.
- **Tối giản & Thẩm mỹ (Aesthetic & Minimalist Design):** Chỉ giữ đúng 4 màn hình chứng minh giá trị cốt lõi MVP, bố cục nhất quán (Header → 4 KPI → AI Banner → 2 cột Biểu đồ → Chi tiết).
- **Trải nghiệm Zero-Friction cho lần đầu mở app:** Nạp sẵn dữ liệu mẫu sinh viên ngay lập tức nên BGK hay người thử nghiệm không bị chặn ở màn hình trống.

---

## 4. Kết luận Nghiệm thu Phần Việc Member 1
Frontend Streamlit 4 màn hình, hệ thống thiết kế và bộ tài liệu sản phẩm đã đạt trạng thái **Ready for Team Integration & Demo**.
