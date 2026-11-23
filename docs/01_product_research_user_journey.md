# 01. Nghiên cứu Pain Point, User Persona & User Journey — MoneyLens AI

> **Phụ trách:** Member 1 — Product & Frontend (`Product Owner`)  
> **Tên sản phẩm:** **MoneyLens AI** — *Your money, understood. Your future, predicted.*  
> **Đối tượng mục tiêu đầu tiên:** Sinh viên đại học và người trẻ mới đi làm (18–26 tuổi) tại Việt Nam.

---

## 1. Bối cảnh thực tế (Real-World Scenario)

Một sinh viên hoặc nhân viên trẻ tại Việt Nam trong 1 tháng trung bình sử dụng từ **5 đến 7 nền tảng giao dịch khác nhau**:

| Kênh thanh toán / Nền tảng | Nhóm chi tiêu điển hình | Tần suất |
|---|---|---|
| **Shopee, TikTok Shop, Lazada** | Quần áo, mỹ phẩm, đồ công nghệ, phụ kiện sale 10.10 / 11.11 | 6–15 đơn/tháng |
| **MoMo / ZaloPay / VNPay QR** | Cà phê (Highlands, Phúc Long), ăn trưa, GrabFood/ShopeeFood | 25–40 lần/tháng |
| **Ngân hàng (MB, Techcombank, VCB...)** | Chuyển khoản tiền trọ, chia tiền ăn nhóm, nhận lương/trợ cấp | 10–20 lần/tháng |
| **Dịch vụ đăng ký định kỳ (Subscriptions)** | Spotify Premium, Netflix, iCloud+, YouTube Premium, 4G Viettel | 4–7 gói/tháng |
| **Hóa đơn thiết yếu** | Tiền thuê phòng, điện nước, Internet FPT, học phí, lệ phí thi | 4–6 hóa đơn/tháng |

Vì **mỗi nền tảng lưu lịch sử giao dịch riêng biệt**, bức tranh tài chính cá nhân bị phân mảnh nghiêm trọng.

---

## 2. Phân tích Pain Point cốt lõi

### Pain Point trung tâm
> *"Người dùng có nhiều giao dịch online nhưng không thực sự hiểu thói quen chi tiêu của mình — và thường chỉ nhận ra mình tiêu quá nhiều khi tài khoản gần cạn ở cuối tháng."*

### 5 Nỗi đau cụ thể cần giải quyết
1. **Mù mờ tổng chi tháng:** Không biết chính xác tháng này đã tiêu tổng cộng bao nhiêu tiền và còn bao nhiêu so với ngân sách.
2. **Bẫy đăng ký tự động (Subscription Fatigue):** Quên các gói tự động gia hạn (Spotify, Netflix, iCloud, 4G...) âm thầm trừ tiền hàng tháng, cộng dồn lên hàng triệu đồng mỗi năm.
3. **Hiệu ứng "rò rỉ nhỏ lặp lại" (Latte Factor):** Khó phát hiện những khoản chi nhỏ 45k–70k (cà phê, trà sữa, đặt đồ ăn vặt) lặp đi lặp lại thành hàng triệu đồng.
4. **Không thấy điểm thất thoát theo danh mục:** Không biết tháng này danh mục nào đang tăng đột biến (VD: Mua sắm tăng vọt dịp sale 11.11).
5. **Thiếu công cụ dự báo trước quyết định mua lớn:** Khi muốn mua laptop 15 triệu hay đi du lịch, người dùng chỉ "ước chừng bằng cảm tính" thay vì nhìn thấy tác động thực sự lên số dư cuối tháng.

---

## 3. Chân dung người dùng điển hình (Target User Persona)

- **Tên đại diện:** Nguyễn Minh Anh (21 tuổi)
- **Vai trò:** Sinh viên năm 3 ngành Kinh tế / CNTT, đang đi thực tập part-time tại TP.HCM / Hà Nội.
- **Thu nhập hàng tháng:** ~11.000.000 – 12.500.000 ₫ (lương thực tập 8tr + trợ cấp gia đình 3tr + freelance 1–1.5tr).
- **Thói quen công nghệ:** Thanh toán không tiền mặt 90% qua QR/ví điện tử, ngại nhập tay từng giao dịch hàng ngày vào app ghi chép truyền thống (bỏ cuộc sau 5 ngày).
- **Mục tiêu:** Muốn tải nhanh file sao kê/CSV một lần là thấy ngay mình đang tiêu lệch ở đâu, tháng này có bị âm tiền không, và có đủ tiền mua laptop mới hay không.

---

## 4. Định vị giá trị sản phẩm (Value Proposition)

Tên gọi **MoneyLens AI** truyền tải 2 giá trị cốt lõi:
- **Lens (Thấu kính):** Nhìn thấu bức tranh dòng tiền phân mảnh chỉ trong vài giây.
- **AI (Trí tuệ nhân tạo):** Tự động hiểu dữ liệu giao dịch, phát hiện bất thường, dự báo số dư tương lai và tư vấn theo ngữ cảnh thực tế của từng người.

---

## 5. Hành trình người dùng 5 bước (User Journey Map)

| Bước | Giai đoạn | Hành động của người dùng | Hệ thống MoneyLens AI xử lý | Màn hình tương ứng | Giá trị cảm xúc |
|---|---|---|---|---|---|
| **1** | **Upload transaction history** | Tải lên file CSV giao dịch (5 cột chuẩn) hoặc bật dữ liệu mẫu sinh viên đã ẩn danh | Kiểm tra định dạng 5 cột, chuẩn hóa số tiền VND dương, làm sạch dòng lỗi | **Sidebar & Screen 1 (Overview)** | Nhanh gọn, không cần nhập tay hay liên kết tài khoản ngân hàng nhạy cảm |
| **2** | **AI understands transactions** | Xem bảng tổng quan & giao dịch tự động gán nhãn ✨ | Phân loại `income`/`expense` vào 6 danh mục chuẩn (*Ăn uống, Mua sắm, Di chuyển, Hóa đơn, Giải trí, Khác*) và nhận diện chi định kỳ | **Screen 1 (Overview) & Screen 2 (Spending)** | Ngạc nhiên vì dữ liệu thô lập tức có cấu trúc rõ ràng |
| **3** | **Discover spending patterns** | Khám phá biểu đồ tỷ trọng, nhóm tăng mạnh, giao dịch bất thường & subscriptions | Phát hiện danh mục tăng >20% MoM, chấm đỏ giao dịch đột biến (>2.2x TB), liệt kê chi phí định kỳ + tổng chi/năm | **Screen 2 (Spending Insights)** | "À hóa ra tháng này mình bị vọt mạnh ở Shopee 11.11!" |
| **4** | **Predict financial future** | Xem đường dự báo số dư 30 ngày tới & thử kéo thanh trượt kịch bản What-If | Tính tốc độ đốt tiền/ngày + hóa đơn định kỳ sắp tới → Dự báo số dư cuối tháng, % rủi ro vượt ngân sách, mô phỏng cắt giảm / mua lớn | **Screen 3 (Financial Forecast)** | Chủ động điều chỉnh trước khi quá muộn |
| **5** | **Ask MoneyLens** | Hỏi bằng tiếng Việt tự nhiên (*"Tôi tiêu nhiều nhất vào đâu?"*, *"Mua laptop 15tr thì sao?"*) | Truy xuất trực tiếp số liệu thực của người dùng → Trả lời cụ thể bằng VND + biểu đồ minh họa + gợi ý hành động | **Screen 4 (AI Advisor)** | Cảm giác có một cố vấn tài chính riêng am hiểu dữ liệu của mình |

---

## 6. Phạm vi MVP — Nguyên tắc cắt giảm thông minh

> **Nguyên tắc:** *Trong cuộc thi, một sản phẩm chạy mượt từ đầu đến cuối có giá trị gấp 10 lần một sản phẩm nhiều tính năng nhưng dang dở.*

| Tính năng | Quyết định | Lý do chiến lược |
|---|---|---|
| Upload file CSV (5 cột chuẩn) | ✅ **Làm** | Đầu vào nhanh, an toàn quyền riêng tư, dễ demo ngay trước BGK |
| Tự động phân loại giao dịch | ✅ **Làm** | AI core chứng minh khả năng hiểu dữ liệu giao dịch thực tế |
| Phân tích thói quen, bất thường & định kỳ | ✅ **Làm** | Tạo ra giá trị "nhìn thấu" trực diện cho người dùng |
| Dự báo số dư cuối tháng & Kịch bản What-If | ✅ **Làm** | Điểm khác biệt cốt lõi so với app ghi chép chi tiêu thông thường |
| Chat với AI Advisor dựa trên dữ liệu thật | ✅ **Làm** | Trải nghiệm demo ấn tượng nhất trước giám khảo |
| Kết nối ngân hàng thật (Open Banking) | ❌ **Bỏ** | Rào cản pháp lý/bảo mật, quá tốn thời gian cho MVP |
| Kết nối MoMo API | ❌ **Bỏ** | Không cần thiết để chứng minh giá trị cốt lõi MVP |
| Quản lý đầu tư, chứng khoán, crypto | ❌ **Bỏ** | Ngoài phạm vi bài toán dòng tiền sinh viên |
| Mobile App riêng (iOS/Android) | ❌ **Bỏ** | Web Dashboard Streamlit chạy mượt là đủ thuyết phục cho demo |

---

## 7. Chỉ số đo lường thành công (MVP Success Metrics)

- **Time-to-First-Insight:** `< 5 giây` kể từ lúc tải file CSV lên đến khi hiển thị đủ 4 màn hình phân tích.
- **Tỷ lệ phân loại tự động hợp lệ:** `>= 85%` trên các dòng giao dịch trống `category`.
- **Trải nghiệm không lỗi (Zero-Crash Demo):** Xử lý an toàn mọi file CSV lỗi định dạng, số âm hoặc thiếu dòng mà không văng traceback.
- **Độ bám dữ liệu của AI Advisor:** 100% câu trả lời mẫu trích dẫn đúng con số VND thực tế từ file CSV đang tải.
