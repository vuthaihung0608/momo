# 04. Kịch bản Demo Trực Tiếp (Live Demo Script) — MoneyLens AI

> **Phụ trách:** Member 1 — Product & Frontend (`Product Owner`)  
> **Người điều khiển demo:** Member 1 (hoặc Member 1 thuyết minh, Member 3 thao tác)  
> **File chuẩn bị sẵn trên Desktop trước giờ thi:** `docs/member1_test_transactions.csv`

---

## Checklist Chuẩn Bị 5 Phút Trước Khi Lên Sân Khấu
- [ ] Mở sẵn Streamlit ở chế độ toàn màn hình (`F11`), zoom trình duyệt `100%` (hoặc `90%` nếu máy chiếu độ phân giải 720p).
- [ ] Kiểm tra URL hoạt động mượt: `http://localhost:8501` (hoặc link Streamlit Cloud sau khi Member 3 deploy).
- [ ] Đặt sẵn file `member1_test_transactions.csv` ở thư mục dễ tìm để demo bước Upload CSV.
- [ ] Đảm bảo đang đứng ở **Screen 1 — Tổng quan tài chính**, chọn **Tháng 11/2026**, ngân sách `9.500.000 ₫`.
- [ ] Chuẩn bị sẵn phương án dự phòng: Nếu mạng phòng thi yếu khiến LLM API bên ngoài chậm, **Frontend Analytics Engine** tích hợp sẵn trong MoneyLens AI vẫn trả lời & vẽ biểu đồ ngay lập tức `< 0.5s`!

---

## Kịch bản 3 Phút (Chuẩn Hackathon / Cuộc thi Sinh viên)

### ⏱️ 0:00 – 0:40 | Screen 1 — Tổng quan tài chính & Upload CSV (Bước 1 & 2 User Journey)
- **Thao tác trên màn hình:**
  1. Chỉ vào Sidebar và mở Expander **"📤 Tải lên lịch sử giao dịch CSV của bạn"**.
  2. Kéo thả file `member1_test_transactions.csv` (94 giao dịch trong 3 tháng của 1 sinh viên đi thực tập, trong đó **có 13 dòng cố tình để trống cột `category`**).
  3. Chỉ vào thông báo xanh: *"Đã nhập thành công 94 giao dịch (tự động phân loại 13 dòng trống danh mục)"*.
  4. Cuộn nhẹ qua **4 thẻ KPI** (Thu `12.400.000 ₫`, Chi `10.685.000 ₫`, Số dư `10.466.000 ₫`, Tiến độ ngân sách `112% — Vượt 1.185.000 ₫`), bấm chuyển tab `Số dư dòng tiền` ↔ `Thu vs Chi`, rồi chỉ nhanh biểu tượng `✨` ở bảng **Giao dịch gần đây**.
- **Lời thoại mẫu:**  
  *"Đây là giao diện thực tế của MoneyLens AI. Người dùng chỉ cần kéo thả file CSV 5 cột đã ẩn thông tin cá nhân — không cần kết nối tài khoản ngân hàng nhạy cảm. Ngay lập tức, hệ thống làm sạch 94 giao dịch, tự động phân loại 13 dòng bị trống danh mục có gắn dấu sao ✨, và cảnh báo ngay rằng tháng 11 này bạn ấy đã chi **10,68 triệu** — vượt ngân sách 9,5 triệu hơn 1,18 triệu đồng."*

---

### ⏱️ 0:40 – 1:25 | Screen 2 — Phân tích chi tiêu (Bước 3 User Journey)
- **Thao tác trên màn hình:**
  1. Bấm menu sidebar sang **🍩 02 · Phân tích chi tiêu**.
  2. Chỉ vào **AI Spike Banner** phía trên: *Mua sắm tăng +281% · Ăn uống tăng +27% so với tháng 10*.
  3. Rê chuột vào biểu đồ **Donut 6 danh mục** (chỉ rõ *Mua sắm chiếm 42,6%*), và chỉ cột màu đỏ nổi bật ở biểu đồ so sánh tháng trước.
  4. Cuộn xuống 2 khung dưới cùng:
     - Trái: **🚨 Giao dịch bất thường** — chỉ ngay **`Shopee 11.11 - Tai nghe Sony chống ồn` (2.650.000 ₫ — gấp 6.9x trung bình danh mục)**.
     - Phải: **🔁 Chi tiêu định kỳ & Subscriptions** — chỉ rõ **`Spotify Premium (59k)`, `Netflix (108k)`, `iCloud+ (19k)`, `Tiền phòng trọ`, `Điện nước`** kèm tổng chi phí quy đổi theo năm.
- **Lời thoại mẫu:**  
  *"Tại sao tháng 11 lại vượt ngân sách? Sang màn hình Spending Insights, MoneyLens trả lời ngay lập tức: nhóm Mua sắm tăng vọt **+281%** do đợt sale 11.11, nổi bật là giao dịch bất thường mua tai nghe Sony 2,65 triệu gấp gần 7 lần mức trung bình. Ở bên phải, hệ thống cũng tự bóc tách 7 khoản định kỳ hàng tháng như Spotify, Netflix, iCloud+, tiền trọ... giúp người dùng không còn bị quên các gói tự gia hạn."*

---

### ⏱️ 1:25 – 2:15 | Screen 3 — Dự báo tài chính & What-If Simulator (Bước 4 User Journey)
- **Thao tác trên màn hình:**
  1. Bấm menu sidebar sang **📈 03 · Dự báo tài chính**.
  2. Chỉ vào **Biểu đồ Dự báo 30 ngày** có mốc đường đứt nét **`Hôm nay (21/11)`** và rủi ro vượt ngân sách `95%`.
  3. **Khoảnh khắc "WOW" #1:** Bấm nút preset **`💻 Mua Laptop`** ở khung *What-If Simulator* bên phải!
     - Màn hình lập tức cập nhật: đường dự báo cắm xuống **vùng ĐỎ thâm hụt (`-1.491.382 ₫`)** so với đường chấm gốc!
  4. **Khoảnh khắc "WOW" #2:** Bấm sang nút preset **`🌱 Tiết kiệm`** (giảm 20% ăn uống, 35% mua sắm, tạm hủy subscription) → đường dự báo bật xanh và ô kết quả hiện ngay số tiền **tiết kiệm thêm** sau 30 ngày!
- **Lời thoại mẫu:**  
  *"Điểm khác biệt lớn nhất của MoneyLens AI nằm ở khả năng nhìn trước tương lai. Dựa trên tốc độ chi hàng ngày và lịch hóa đơn định kỳ 30 ngày tới, biểu đồ dự báo rõ đường dòng tiền sau mốc hôm nay. Nếu bạn sinh viên này đang định mua một chiếc laptop 15 triệu — chỉ cần bấm mô phỏng, vùng đỏ xuất hiện cảnh báo ngay tài khoản sẽ bị âm gần 1,5 triệu đồng. Ngược lại, khi thử kịch bản Tiết kiệm, bạn thấy ngay mình giữ lại thêm được bao nhiêu tiền trước khi quyết định!"*

---

### ⏱️ 2:15 – 3:00 | Screen 4 — Trợ lý AI Advisor (Bước 5 User Journey)
- **Thao tác trên màn hình:**
  1. Bấm menu sidebar sang **✨ 04 · Trợ lý AI Advisor**.
  2. Bấm nhanh nút câu hỏi mẫu #1: **`💬 Tôi tiêu nhiều nhất vào đâu?`** → Chỉ câu trả lời có số liệu chính xác (`Mua sắm 42.6%`) + **biểu đồ cột nhúng trực tiếp trong khung chat**.
  3. Bấm nhanh nút câu hỏi mẫu #2: **`💬 Nếu tháng sau tôi mua laptop 15 triệu thì sao?`** → Chỉ câu trả lời phân tích số dư trước/sau (`-1.491.382 ₫`), đề xuất **trả góp 0% 6 tháng (~2,5 triệu/tháng)** + biểu đồ so sánh 3 cột.
- **Lời thoại mẫu:**  
  *"Cuối cùng, thay vì tự đọc bảng biểu, người dùng chỉ cần trò chuyện tự nhiên với MoneyLens AI. Khi hỏi 'Tôi tiêu nhiều nhất vào đâu?' hay 'Nếu tháng sau tôi mua laptop 15 triệu thì sao?', trợ lý trả lời trực diện bằng con số VND thật từ dữ liệu của chính người dùng, đính kèm biểu đồ minh họa và gợi ý giải pháp hành động rõ ràng. Đây chính là cách MoneyLens AI giúp người trẻ làm chủ dòng tiền chỉ trong vài phút. Em xin cảm ơn Ban Giám Khảo!"*

---

## Phiên bản Mở rộng 5 Phút (Thêm 2 phút tương tác sâu)
Nếu BGK cho thêm thời gian demo:
- **+45 giây:** Ở Screen 1, gõ `"Highlands"` vào ô tìm kiếm Giao dịch gần đây để minh chứng khả năng truy xuất nhanh các khoản cà phê nhỏ lặp lại (giải quyết pain point #3).
- **+45 giây:** Ở Screen 3, kéo thử thanh trượt **Giảm Mua sắm** bằng tay + nhập thử khoản mua tùy ý do BGK đề xuất (VD: *"Đi du lịch Đà Lạt 4 triệu"*).
- **+30 giây:** Ở Screen 4, gõ trực tiếp một câu hỏi bất kỳ từ BGK vào ô chat (VD: *"Làm sao để tôi tiết kiệm thêm 2 triệu mỗi tháng?"*).
