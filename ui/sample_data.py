"""Realistic Vietnamese student & young professional sample dataset for MoneyLens AI.

Follows the exact 5-column team CSV contract:
    date, description, amount, type, category
- type: 'income' or 'expense'
- amount: positive VND number
- category: may be empty ('') to demonstrate automatic categorization
"""

from __future__ import annotations

import io
from pathlib import Path
import pandas as pd

SAMPLE_CSV_CONTENT = """date,description,amount,type,category
2026-09-01,Lương thực tập tháng 9,7500000,income,Income
2026-09-01,Tiền thuê phòng trọ,3200000,expense,Bills
2026-09-02,Highlands Coffee,45000,expense,Food
2026-09-02,Cơm tấm sườn bì chả,45000,expense,Food
2026-09-03,GrabBike đi làm,32000,expense,Transport
2026-09-04,Trợ cấp gia đình tháng 9,3000000,income,Income
2026-09-04,Shopee đơn hàng đồ gia dụng,245000,expense,Shopping
2026-09-05,Spotify Premium,59000,expense,Entertainment
2026-09-06,Bún bò Huế bữa trưa,50000,expense,Food
2026-09-07,Đổ xăng Petrolimex,80000,expense,Transport
2026-09-08,Netflix Standard,108000,expense,Entertainment
2026-09-09,GrabFood gà rán tối,115000,expense,Food
2026-09-10,iCloud+ 50GB,19000,expense,Entertainment
2026-09-11,Nhà sách Fahasa mua giáo trình,280000,expense,Other
2026-09-12,Cước 4G Viettel,120000,expense,Bills
2026-09-13,Phúc Long Tea cùng bạn,110000,expense,Food
2026-09-14,TikTok Shop áo thun basic,189000,expense,Shopping
2026-09-15,Internet FPT,180000,expense,Bills
2026-09-16,Xanh SM đi gặp nhóm,48000,expense,Transport
2026-09-17,Lẩu Haidilao sinh nhật bạn,420000,expense,Food
2026-09-18,CGV Cinemas xem phim cuối tuần,165000,expense,Entertainment
2026-09-19,Freelance thiết kế slide,1200000,income,Income
2026-09-20,Tiền điện nước phòng trọ,430000,expense,Bills
2026-09-21,ShopeeFood trà sữa Mixue,65000,expense,Food
2026-09-22,Cắt tóc 30Shine,120000,expense,Other
2026-09-23,Shopee phụ kiện laptop,310000,expense,Shopping
2026-09-24,Cơm văn phòng trưa,55000,expense,Food
2026-09-25,GrabBike đi học tối,35000,expense,Transport
2026-09-26,Siêu thị WinMart mua đồ ăn,360000,expense,Food
2026-09-27,Đổ xăng Petrolimex,85000,expense,Transport
2026-09-28,Bida cuối tuần cùng bạn,140000,expense,Entertainment
2026-09-29,Nhà thuốc Long Châu,150000,expense,Other
2026-09-30,Highlands Coffee chạy deadline,55000,expense,Food
2026-10-01,Lương thực tập tháng 10,8000000,income,Income
2026-10-01,Tiền thuê phòng trọ,3200000,expense,Bills
2026-10-02,Highlands Coffee,45000,expense,
2026-10-03,Phở bò bữa sáng,45000,expense,Food
2026-10-04,Trợ cấp gia đình tháng 10,3000000,income,Income
2026-10-04,GrabBike đi thực tập,38000,expense,
2026-10-05,Spotify Premium,59000,expense,Entertainment
2026-10-06,Shopee 10.10 giày sneaker,590000,expense,Shopping
2026-10-07,GrabFood bún đậu mắm tôm,98000,expense,Food
2026-10-08,Netflix Standard,108000,expense,Entertainment
2026-10-09,Đổ xăng Petrolimex,80000,expense,Transport
2026-10-10,iCloud+ 50GB,19000,expense,Entertainment
2026-10-10,TikTok Shop skincare dưỡng ẩm,265000,expense,Shopping
2026-10-12,Cước 4G Viettel,120000,expense,Bills
2026-10-13,Katinat Coffee & Tea,65000,expense,Food
2026-10-14,Siêu thị Circle K đồ ăn vặt,85000,expense,Food
2026-10-15,Internet FPT,180000,expense,Bills
2026-10-16,Xanh SM đi hội thảo,62000,expense,Transport
2026-10-17,Đóng lệ phí thi chứng chỉ,650000,expense,Other
2026-10-18,Freelance chỉnh sửa video,1500000,income,Income
2026-10-19,CGV Cinemas vé xem phim,175000,expense,Entertainment
2026-10-20,Tiền điện nước phòng trọ,455000,expense,Bills
2026-10-21,ShopeeFood cơm gà xối mỡ,72000,expense,Food
2026-10-22,MoMo thanh toán ăn nướng,390000,expense,Food
2026-10-23,Shopee mua balo đi học,340000,expense,Shopping
2026-10-24,GrabBike về trọ mưa gió,45000,expense,Transport
2026-10-25,WinMart mua trái cây và sữa,290000,expense,Food
2026-10-26,Boardgame café cùng nhóm,130000,expense,Entertainment
2026-10-27,Đổ xăng Petrolimex,85000,expense,Transport
2026-10-28,Quà tặng sinh nhật bạn thân,320000,expense,Other
2026-10-29,Highlands Coffee học nhóm,55000,expense,Food
2026-10-30,ShopeeFood đặt trà sữa,68000,expense,Food
2026-11-01,Lương thực tập tháng 11,8000000,income,Income
2026-11-01,Tiền thuê phòng trọ,3200000,expense,Bills
2026-11-01,Highlands Coffee,45000,expense,Food
2026-11-02,Cơm tấm trưa gần trường,50000,expense,
2026-11-03,GrabBike đi làm sáng,36000,expense,
2026-11-04,Trợ cấp gia đình tháng 11,3000000,income,Income
2026-11-04,Shopee mua đèn bàn học,275000,expense,
2026-11-05,Spotify Premium,59000,expense,
2026-11-06,GrabFood pizza nhóm dự án,245000,expense,Food
2026-11-07,Đổ xăng Petrolimex,85000,expense,Transport
2026-11-08,Netflix Standard,108000,expense,Entertainment
2026-11-09,Phúc Long Tea buổi chiều,65000,expense,
2026-11-10,iCloud+ 50GB,19000,expense,Entertainment
2026-11-10,TikTok Shop áo khoác mùa đông,460000,expense,Shopping
2026-11-11,Shopee 11.11 - Tai nghe Sony chống ồn,2650000,expense,Shopping
2026-11-11,Shopee 11.11 combo đồ skincare & phụ kiện,580000,expense,
2026-11-12,Cước 4G Viettel,120000,expense,
2026-11-13,MoMo thanh toán lẩu băng chuyền,460000,expense,Food
2026-11-14,Xanh SM đi thuyết trình,72000,expense,Transport
2026-11-15,Internet FPT,180000,expense,Bills
2026-11-15,Uniqlo mua sơ mi đi phỏng vấn,590000,expense,Shopping
2026-11-16,Freelance hỗ trợ làm landing page,1400000,income,Income
2026-11-17,CGV Cinemas & bắp nước,195000,expense,
2026-11-18,ShopeeFood cơm trưa và trà đào,92000,expense,
2026-11-19,GrabBike đi họp hackathon,44000,expense,Transport
2026-11-20,Tiền điện nước phòng trọ,475000,expense,
2026-11-20,Siêu thị WinMart đồ ăn tuần,340000,expense,Food
2026-11-21,Highlands Coffee hoàn thiện demo,55000,expense,
2026-11-21,Katinat Coffee mua cho team,185000,expense,Food
"""

TEMPLATE_CSV_CONTENT = """date,description,amount,type,category
2026-11-01,Lương part-time tháng 11,8000000,income,Income
2026-11-01,Tiền thuê phòng trọ,3200000,expense,Bills
2026-11-01,Highlands Coffee,45000,expense,Food
2026-11-02,Shopee mua sách và phụ kiện,250000,expense,
2026-11-03,GrabBike đi học,35000,expense,
2026-11-05,Spotify Premium,59000,expense,Entertainment
"""


def get_sample_dataframe() -> pd.DataFrame:
    """Load team's data/sample_transactions.csv if available, else built-in demo data."""
    project_root = Path(__file__).resolve().parent.parent
    team_sample = project_root / "data" / "sample_transactions.csv"
    if team_sample.exists():
        return pd.read_csv(team_sample, dtype={"category": str}).fillna({"category": ""})
    return pd.read_csv(io.StringIO(SAMPLE_CSV_CONTENT), dtype={"category": str}).fillna({"category": ""})


def get_sample_csv_bytes() -> bytes:
    """Return UTF-8 bytes of the full demo CSV for download/testing."""
    project_root = Path(__file__).resolve().parent.parent
    team_sample = project_root / "data" / "sample_transactions.csv"
    if team_sample.exists():
        return team_sample.read_bytes()
    return SAMPLE_CSV_CONTENT.encode("utf-8-sig")


def get_template_csv_bytes() -> bytes:
    """Return a clean 5-column CSV template for users to fill in."""
    return TEMPLATE_CSV_CONTENT.encode("utf-8-sig")
