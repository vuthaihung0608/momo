# 03. Nội dung Slide Thuyết Trình (Pitch Deck — 10 Slides) — MoneyLens AI

> **Phụ trách:** Member 1 — Product & Frontend (`Product Owner`)  
> **Thời lượng chuẩn:** 5 phút thuyết trình + 3 phút Live Demo (tổng 8 phút) hoặc rút gọn 5 phút trọn gói.

---

## Slide 1 — Trang bìa (Title Slide)
- **Tiêu đề lớn:** **MoneyLens AI**
- **Tagline:** *Your money, understood. Your future, predicted.*
- **Phụ đề:** Trợ lý tài chính cá nhân ứng dụng AI giúp sinh viên & người trẻ nhìn thấu chi tiêu và dự báo dòng tiền.
- **Visual:** Mockup màn hình `Financial Forecast` & logo kính lúp `🔎` trên nền gradient Indigo → Sky.
- **Speaker Note (Member 1 — 15s):**  
  *"Xin chào Ban Giám Khảo! Có bao giờ các bạn sinh viên ở cuối tháng mở app ngân hàng và tự hỏi: 'Ủa, lương và tiền trợ cấp đi đâu hết rồi?' Đó chính là lý do nhóm chúng em tạo ra **MoneyLens AI** — thấu kính AI giúp bạn không chỉ biết tiền đã đi đâu, mà còn dự báo tương lai tài chính của chính mình."*

---

## Slide 2 — Vấn đề thực tế (The Problem)
- **Headline:** Chi tiêu online càng tiện, túi tiền càng... "tàng hình"
- **4 gạch đầu dòng súc tích:**
  - Giao dịch phân mảnh trên **5–7 nền tảng**: Shopee, TikTok Shop, MoMo, ngân hàng, Spotify/Netflix, hóa đơn phòng trọ.
  - Quên các khoản **đăng ký tự động định kỳ** âm thầm trừ tiền hàng tháng.
  - Không thấy các **khoản chi nhỏ lặp lại** (cà phê 45k, trà sữa, GrabFood) cộng dồn hàng triệu đồng.
  - Chỉ nhận ra mình tiêu vượt ngân sách **khi đã quá muộn**.
- **Visual:** Hình ghép các ứng dụng thanh toán quen thuộc tại Việt Nam (Shopee, MoMo, Spotify, Bank QR) dẫn vào dấu chấm hỏi lớn.
- **Speaker Note (30s):** Nhấn mạnh pain point của sinh viên & người trẻ mới đi làm — không ai kiên trì nhập tay từng ly cà phê 45.000đ mỗi ngày.

---

## Slide 3 — Giải pháp: MoneyLens AI
- **Headline:** Một file CSV. 5 giây phân tích. Nhìn thấu hiện tại & dự báo tương lai.
- **2 trụ cột giá trị:**
  - **🔎 Lens (Nhìn thấu):** Gom toàn bộ giao dịch vào một dashboard trực quan, tự phân loại danh mục, bóc tách chi phí định kỳ & giao dịch bất thường.
  - **✨ AI (Hiểu & Dự báo):** Dự báo số dư cuối tháng, mô phỏng kịch bản chi tiêu (*What-If*) và trò chuyện hỏi đáp trực tiếp trên số liệu thật.
- **Visual:** Sơ đồ 5 bước User Journey (`Upload CSV` → `AI Understands` → `Discover Patterns` → `Predict Future` → `Ask MoneyLens`).

---

## Slide 4 — Phạm vi MVP thông minh (Why We Built What Matters)
- **Headline:** Tập trung 100% vào giá trị cốt lõi — Chạy mượt từ đầu đến cuối
- **Bảng 2 cột (Làm vs Chưa làm ở MVP):**
  - ✅ **MVP Đã hoàn thiện:** Upload CSV chuẩn 5 cột · Tự động phân loại 6 danh mục · Phát hiện bất thường & định kỳ · Dự báo 30 ngày + Kịch bản What-If · AI Advisor hỏi đáp.
  - ⏭️ **Lộ trình giai đoạn sau:** Open Banking API, kết nối ví MoMo tự động, Mobile App, quản lý đầu tư.
- **Speaker Note (20s):** Thể hiện tư duy sản phẩm trưởng thành — ưu tiên bảo mật (CSV ẩn danh), tránh over-engineering để đảm bảo sản phẩm chạy thật 100%.

---

## Slide 5 — 4 Màn hình cốt lõi của Sản phẩm (Product Showcase)
- **Headline:** Trải nghiệm liền mạch qua 4 màn hình trọng tâm
- **Layout 2×2 ảnh chụp thật từ Streamlit App:**
  1. **Overview:** Tổng thu, tổng chi, số dư, thanh ngân sách, dòng tiền & giao dịch gần đây.
  2. **Spending Insights:** Top danh mục, xu hướng tăng mạnh (+281% Mua sắm 11.11), bất thường & định kỳ.
  3. **Financial Forecast:** Đường dự báo vùng Xanh/Đỏ + thanh trượt kịch bản *Mua Laptop 15 triệu / Tiết kiệm*.
  4. **AI Advisor:** Hỏi tiếng Việt tự nhiên, trả lời kèm con số VND thật và biểu đồ nhúng.

---

## Slide 6 — Kiến trúc kỹ thuật & Tech Stack (Member 2 & 3 trình bày)
- **Headline:** Kiến trúc tinh gọn, dễ mở rộng, không lạm dụng công nghệ thừa
- **Sơ đồ 4 tầng:**
  - **User Interface:** Streamlit + Plotly (Member 1)
  - **Data Processing:** Pandas · NumPy · Quy ước CSV 5 cột VND (Member 3)
  - **ML Engine:** Scikit-learn (Phân loại giao dịch) + Rule-based (Định kỳ/Bất thường) + Forecasting (Member 2)
  - **AI Assistant:** Gemini LLM API diễn giải dựa trên dữ liệu thực tế (Member 3)
- **Điểm nhấn kỹ thuật:** Chọn ML truyền thống + Baseline dự báo minh bạch thay vì Deep Learning nặng nề — tốc độ phản hồi `< 1 giây`, dễ giải thích kết quả.

---

## Slide 7 — LIVE DEMO (Điểm sáng ăn điểm tuyệt đối!)
- **Headline:** Trải nghiệm trực tiếp **MoneyLens AI**
- **On-slide checklist ngắn gọn (3 kịch bản demo):**
  1. Tải file CSV có dòng trống danh mục → Tự phân loại tức thì.
  2. Soi bất thường `Tai nghe Sony 2.65tr` & các gói `Spotify/Netflix`.
  3. Hỏi AI: *"Nếu tháng sau tôi mua laptop 15 triệu thì sao?"* → Xem cảnh báo thâm hụt & giải pháp.
- *(Chuyển sang cửa sổ trình duyệt chạy Streamlit — xem chi tiết tại `04_demo_script.md`)*

---

## Slide 8 — Kiểm thử trải nghiệm & Kết quả đánh giá (Member 1 + Member 2)
- **Headline:** Đã kiểm thử thực tế với dữ liệu 3 tháng & 15 kịch bản biên
- **3 thẻ số liệu nổi bật:**
  - **100%** xử lý an toàn file CSV thiếu cột, số tiền âm hoặc trống danh mục.
  - **< 2 giây** từ lúc tải file đến khi tạo đủ biểu đồ 4 màn hình.
  - **0 hallucination** trên các câu hỏi số liệu cốt lõi nhờ tính toán trực tiếp từ DataFrame trước khi diễn giải.

---

## Slide 9 — Khả năng mở rộng & Tương lai (Roadmap)
- **Headline:** Từ trợ lý sinh viên đến nền tảng sức khỏe tài chính thế hệ mới
- **3 mốc phát triển:**
  - **Phase 1 (Hiện tại — MVP):** Web App nhập CSV ẩn danh, phân loại, dự báo 30 ngày & AI Advisor.
  - **Phase 2 (3–6 tháng):** Tự động đọc sao kê PDF/Excel ngân hàng Việt Nam (MB, VCB, Techcombank, MoMo) & cảnh báo định kỳ qua Email/Telegram.
  - **Phase 3 (6–12 tháng):** Cá nhân hóa mục tiêu tiết kiệm thông minh, chia nhóm ngân sách sinh viên & tích hợp Open Banking chuẩn Việt Nam.

---

## Slide 10 — Cảm ơn & Hỏi Đáp (Q&A)
- **Headline:** **MoneyLens AI** — *Your money, understood. Your future, predicted.*
- **Thông tin nhóm:**
  - Member 1 — Product & Frontend (`Product Owner`)
  - Member 2 — Data & AI (`AI Owner`)
  - Member 3 — Backend & Integration (`Engineering Owner`)
- **QR Code / Link GitHub & Link Live Demo.**

---

## Bộ 6 Câu Hỏi Phản Biện Thường Gặp từ Ban Giám Khảo & Cách Trả Lời

1. **BGK:** *"Tại sao không kết nối trực tiếp ngân hàng hay MoMo luôn?"*  
   **Trả lời:** Với phạm vi MVP cuộc thi, kết nối Open Banking đòi hỏi giấy phép bảo mật và thời gian tích hợp rất lớn. Dùng CSV xuất từ app ngân hàng/ví điện tử vừa đảm bảo **quyền riêng tư tuyệt đối** (người dùng không cần đưa mật khẩu hay quyền truy cập tài khoản thật), vừa chứng minh trọn vẹn lõi AI phân loại – dự báo – tư vấn.
2. **BGK:** *"AI Advisor có bị 'bịa số' (hallucination) không?"*  
   **Trả lời:** Không! Kiến trúc của nhóm tách bạch **tầng tính toán bằng Python/Pandas** (tính chính xác tổng chi, tỷ lệ %, số dư dự báo bằng công thức) rồi mới đưa số liệu thật đó vào AI diễn giải. Nhờ vậy số VND luôn chính xác 100%.
3. **BGK:** *"Nếu file CSV người dùng tải lên để trống cột `category` hoặc ghi số tiền âm thì sao?"*  
   **Trả lời:** Hệ thống đã được kiểm thử cho các tình huống này: số tiền âm tự chuẩn hóa sang dương kèm thông báo minh bạch, còn mọi dòng trống `category` sẽ được gắn cờ và tự động phân loại (hiển thị biểu tượng `✨`).
4. **BGK:** *"Điểm khác biệt của MoneyLens AI so với MoneyLover hay Sổ Thu Chi MISA?"*  
   **Trả lời:** Các app truyền thống thiên về **ghi chép quá khứ** (và đòi nhập tay mỗi ngày khiến sinh viên dễ bỏ cuộc). MoneyLens AI tập trung vào **phân tích tự động từ lịch sử + dự báo tương lai 30 ngày + mô phỏng kịch bản What-If + hỏi đáp ngôn ngữ tự nhiên**.
5. **BGK:** *"Nếu mới có dữ liệu 1 tháng thì dự báo có chính xác không?"*  
   **Trả lời:** Hệ thống vẫn tính được tốc độ chi tiêu hàng ngày (`daily burn rate`) của tháng đó để ước lượng cuối tháng, đồng thời hiển thị khoảng tin cậy dự báo. Khi người dùng có từ 2–3 tháng trở lên, độ chính xác nhận diện chi định kỳ và xu hướng tăng giảm sẽ càng cao.
6. **BGK:** *"Nhóm phân công công việc thế nào để không bị chồng chéo?"*  
   **Trả lời:** Nhóm chốt sớm 2 hợp đồng chung: **Cấu trúc CSV 5 cột** và **Cấu trúc thư mục GitHub** (Member 1 phụ trách Product & Frontend `app.py`, `pages/*`; Member 2 phụ trách Data & ML; Member 3 phụ trách Backend & LLM `src/*`), kết nối qua lớp `Service Adapter` nên làm song song rất mượt.
