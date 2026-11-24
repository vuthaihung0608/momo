# 02. Tài liệu Thiết kế Giao diện & Hệ thống Thiết kế (Figma Design Spec) — MoneyLens AI

> **Phụ trách:** Member 1 — Product & Frontend (`Product Owner`)  
> **Link Figma thiết kế trực tiếp (Editable Design System + 4 Màn Hình 1440×960):** https://www.figma.com/design/dYLwJMbLYDNNFDNq5riM4A  
> **Bản xem trước HTML offline:** Mở trực tiếp file [figma_prototype_preview.html](./figma_prototype_preview.html) bằng trình duyệt Chrome/Edge.

---

## 1. Triết lý thiết kế (Design Direction)

Lấy cảm hứng từ các ứng dụng FinTech hiện đại (*Fintrack, LumeniFi, Capterra Cash Forecast, NeuroBank AI*):
- **Sạch & Tin cậy (Light FinTech Canvas):** Nền xám lạnh nhẹ `#F8FAFC` kết hợp thẻ trắng sắc nét `#FFFFFF` viền `1px solid #E2E8F0` giúp con số tài chính nổi bật, dễ đọc khi chiếu lên màn hình lớn trong phòng thi.
- **Tín hiệu màu có ngữ nghĩa rõ ràng (Semantic Color Coding):** Người dùng liếc mắt 1 giây hiểu ngay trạng thái *Tích cực (Xanh ngọc)*, *Cảnh báo (Vàng hổ phách)*, *Nguy cơ/Bất thường (Đỏ san hô)*, *Trí tuệ AI (Chàm Indigo)*.
- **Thông tin phân tầng rõ ràng (Visual Hierarchy):** Mỗi màn hình tuân theo cấu trúc chuẩn:
  `Page Header` → `4 KPI Cards` → `AI Highlight Callout` → `Biểu đồ chính (2 cột)` → `Danh sách hành động chi tiết`.

---

## 2. Design Tokens (Sao chép trực tiếp sang Figma Variables)

### 2.1. Bảng màu (Color Palette)

| Token Name | Hex | Vai trò sử dụng |
|---|---|---|
| `Brand / Primary` | `#4F46E5` | Màu chủ đạo MoneyLens AI, CTA, biểu đồ chính, badge AI |
| `Brand / Primary Light` | `#6366F1` | Gradient đầu sidebar, điểm scatter bình thường |
| `Brand / Primary Soft` | `#EEF2FF` | Nền AI Insight Banner, pill badge thông tin |
| `Brand / Sky Accent` | `#0EA5E9` | Điểm nhấn gradient thương hiệu, danh mục Di chuyển |
| `Semantic / Success` | `#10B981` | Thu nhập, dòng tiền dương (vùng xanh dự báo), On Track |
| `Semantic / Success Soft` | `#ECFDF5` | Nền pill tăng trưởng tốt / tiết kiệm |
| `Semantic / Danger` | `#EF4444` | Chi tiêu vượt mức, giao dịch bất thường, vùng âm dự báo |
| `Semantic / Danger Soft` | `#FEF2F2` | Nền cảnh báo vượt ngân sách / anomaly |
| `Semantic / Warning` | `#F59E0B` | Cảnh báo gần chạm hạn mức (80–99%), Subscriptions định kỳ |
| `Neutral / Ink 900` | `#0F172A` | Tiêu đề trang, con số KPI chính |
| `Neutral / Muted 500` | `#64748B` | Nhãn phụ, chú thích trục biểu đồ |
| `Surface / Canvas` | `#F8FAFC` | Nền tổng thể toàn ứng dụng |
| `Surface / Card` | `#FFFFFF` | Nền thẻ KPI, container biểu đồ, sidebar |
| `Surface / Border` | `#E2E8F0` | Viền thẻ 1px và đường phân cách |

### 2.2. Màu sắc 6 danh mục chi tiêu chuẩn

| Category Key | Nhãn tiếng Việt | Icon | Hex Color |
|---|---|---|---|
| `Food` | Ăn uống | 🍜 | `#F97316` (Orange 500) |
| `Shopping` | Mua sắm | 🛍️ | `#8B5CF6` (Violet 500) |
| `Transport` | Di chuyển | 🛵 | `#0EA5E9` (Sky 500) |
| `Bills` | Hóa đơn | 🧾 | `#4F46E5` (Indigo 600) |
| `Entertainment` | Giải trí | 🎬 | `#EC4899` (Pink 500) |
| `Other` | Khác | 📦 | `#64748B` (Slate 500) |

### 2.3. Typography (Font: `Inter` — Google Fonts)

| Style | Size | Weight | Line Height | Ứng dụng |
|---|---|---|---|---|
| `Page Title (H1)` | `26px` (`1.65rem`) | `800 ExtraBold` | `1.2` | Tiêu đề chính mỗi màn hình |
| `KPI Number` | `25px` (`1.55rem`) | `800 ExtraBold` | `1.2` | Tổng thu, tổng chi, số dư VND |
| `Section Title (H2)` | `16px` (`1.0rem`) | `700 Bold` | `1.35` | Tiêu đề thẻ biểu đồ / bảng |
| `Body / Chat` | `14px` (`0.88rem`) | `400 Regular` | `1.5` | Nội dung AI Insight, câu trả lời chat |
| `KPI Label / Caption` | `12.5px` (`0.8rem`) | `600 SemiBold` | `1.3` | Nhãn thẻ KPI (Uppercase tracking `+0.03em`) |
| `Pill Badge` | `12px` (`0.74rem`) | `600 SemiBold` | `1.2` | Pill `+12% vs kỳ trước`, `On Track`, `Subscription` |

### 2.4. Spacing & Radius (8px Grid System)
- **Desktop Frame:** `1440 × 900 px` · Sidebar width: `280px` · Main content max-width: `1320px` · Padding: `24px`.
- **Card Radius:** `16px` (`border-radius: 16px`), padding `18px–20px`.
- **Inner List Item / Input Radius:** `12px`.
- **Pill Badge / Quick Prompt Button Radius:** `999px` (Full pill).
- **Elevation:** `0 1px 3px rgba(15, 23, 42, 0.04)` mặc định; hover `0 10px 25px -10px rgba(15, 23, 42, 0.10)`.

---

## 3. Kiến trúc bố cục 4 màn hình (Wireframe Blueprints)

### Layout dùng chung — Persistent Sidebar (`280px`)
1. **Brand Header Card** (Gradient `#4F46E5 → #0EA5E9`): Logo `🔎 MoneyLens AI` + Tagline.
2. **Primary Navigation (4 màn hình):**
   - `📊 01 · Tổng quan tài chính`
   - `🍩 02 · Phân tích chi tiêu`
   - `📈 03 · Dự báo tài chính`
   - `✨ 04 · Trợ lý AI Advisor`
3. **CSV Upload Module:** Dropzone 5 cột chuẩn + Badge tóm tắt nguồn dữ liệu + 2 nút tải CSV mẫu / Form trống.
4. **Global Controls:** Bộ chọn Tháng hiển thị + Thanh trượt Ngân sách mục tiêu (VND).
5. **Engine Status Footer:** Chỉ báo kết nối backend `src/`.

### Frame 01 — Financial Overview (`pages/overview.py`)
- **Top:** Header + Badge kỳ đang xem + Expander tải CSV nhanh (Bước 1 User Journey).
- **Row 1 (4 cột bằng nhau):** `Tổng thu nhập` | `Tổng chi tiêu` | `Số dư hiện tại` | `Tiến độ ngân sách` (kèm thanh progress đổi màu Xanh/Vàng/Đỏ).
- **Row 2 (Full width):** `AI Quick Insight Banner` tóm tắt nhanh 2 câu về tình hình kỳ này.
- **Row 3 (Tỷ lệ 1.45 : 1):**
  - Trái: `Biểu đồ dòng tiền` (nút chuyển `Số dư dòng tiền` spline area ↔ `Thu vs Chi` grouped bar).
  - Phải: `Donut Chart` tỷ trọng chi tiêu 6 danh mục có tổng chi ở tâm vòng tròn.
- **Row 4 (Full width):** `Bảng giao dịch gần đây` có ô tìm kiếm + lọc Loại (`income`/`expense`) + lọc Danh mục + dấu `✨` cho dòng AI tự phân loại.

### Frame 02 — Spending Insights (`pages/spending.py`)
- **Row 1 (4 cột):** `Tổng chi tiêu` | `Danh mục lớn nhất` | `Số giao dịch bất thường` | `Chi tiêu định kỳ / tháng`.
- **Row 2:** `AI Spike Alert Banner` cảnh báo danh mục tăng vọt >20% so với tháng trước.
- **Row 3 (Tỷ lệ 1.05 : 1.2):**
  - Trái: `Donut Chart` 6 danh mục + Bảng xếp hạng chi tiết (% tỷ trọng, số GD, % thay đổi MoM).
  - Phải (trên): `Biểu đồ xu hướng tăng giảm` (cột đôi so sánh tháng trước/nay — cột đỏ nếu tăng >20% ↔ đường xu hướng nhiều tháng).
  - Phải (dưới): `Scatter Plot` chấm giá trị từng giao dịch (chấm đỏ lớn gắn nhãn giao dịch bất thường).
- **Row 4 (2 cột 50/50):**
  - Trái: Danh sách thẻ cảnh báo `🚨 Giao dịch bất thường` (tên, ngày, số tiền, gấp `x.x` lần TB danh mục).
  - Phải: Danh sách thẻ `🔁 Chi tiêu định kỳ & Subscriptions` (tên dịch vụ, chi phí/tháng, ước tính/năm, ngày trừ dự kiến).

### Frame 03 — Financial Forecast (`pages/forecast.py`)
- **Row 1 (4 cột):** `Số dư dự báo cuối tháng` (kèm pill `An toàn / Cần kiểm soát / Nguy cơ`) | `Dự báo chi tiêu tháng tới` | `Khả năng vượt ngân sách (%)` | `Chi phí định kỳ sắp tới`.
- **Row 2 (Tỷ lệ 1.65 : 1):**
  - Trái (trên): `Projected Cash Balance Chart` — Lịch sử thực tế + đường kẻ dọc `Hôm nay` + Dự báo có **vùng xanh dương (`>=0`)**, **vùng đỏ âm (`<0`)**, khoảng tin cậy mờ, và đường chấm so sánh kịch bản gốc.
  - Trái (dưới): Thẻ `Giải thích xu hướng dự báo` bằng ngôn ngữ tự nhiên dễ hiểu.
  - Phải: `What-If Scenario Simulator` — 3 nút Preset (`🌱 Tiết kiệm` | `💻 Mua Laptop` | `↩️ Mặc định`), 3 thanh trượt cắt giảm % danh mục, công tắc hủy Subscriptions, ô nhập khoản mua lớn đột xuất, và hộp kết quả chênh lệch tiết kiệm/thâm hụt sau 30 ngày.
- **Row 3 (Full width, lưới 2 cột):** `Lịch chi phí định kỳ sắp tới (30 ngày)` với số ngày đếm ngược.

### Frame 04 — AI Advisor (`pages/advisor.py`)
- **Top Strip:** Thanh ngữ cảnh dữ liệu sống (`🧠 Dữ liệu AI đang phân tích`) + nút `🗑️ Hội thoại mới`.
- **Prompt Chips (2 hàng × 3 cột):** 6 câu hỏi gợi ý bấm là chạy ngay, nổi bật 2 câu mẫu trọng tâm:
  1. `"Tôi tiêu nhiều nhất vào đâu?"`
  2. `"Nếu tháng sau tôi mua laptop 15 triệu thì sao?"`
- **Chat Thread:** Bong bóng hội thoại phân biệt rõ User (`🧑`) và MoneyLens AI (`🔎`), hỗ trợ Markdown + **biểu đồ Plotly nhúng trực tiếp ngay trong câu trả lời AI** + chú thích nguồn phân tích.
- **Bottom Sticky Input:** Ô nhập câu hỏi tự nhiên bằng tiếng Việt/tiếng Anh.

---

## 4. Hướng dẫn dựng nhanh lên Figma (Nếu cần nộp link Figma file)
1. Tạo 1 Figma Design File mới tên **`MoneyLens AI — UI/UX System`**.
2. Tạo 2 Pages trong Figma: `01 · Design System` và `02 · 4 MVP Screens (1440x900)`.
3. Copy bảng Color Variables & Text Styles từ Mục 2 ở trên vào **Local Variables**.
4. Mở file [figma_prototype_preview.html](./figma_prototype_preview.html) trong trình duyệt để làm mẫu trực quan (hoặc dùng plugin **html.to.design** trong Figma để import trực tiếp HTML này thành các Figma Layers chỉnh sửa được chỉ trong 30 giây!).
