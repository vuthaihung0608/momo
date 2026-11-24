"""Transaction Auto-Categorization Engine & ML Evaluation (Member 2 — Data & AI).

Uses Scikit-learn TF-IDF (word + character n-grams) + Logistic Regression trained on a
Vietnamese & English student/young-professional FinTech corpus (216 labeled transactions),
paired with a high-precision merchant disambiguation layer and 5-fold Stratified Cross-Validation
benchmarking (Logistic Regression vs Random Forest).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline

EXPENSE_CLASSES = ["Food", "Shopping", "Transport", "Bills", "Entertainment", "Other"]

# Realistic Vietnamese & English student/young-pro FinTech training corpus (36 samples/class = 216 rows)
TRAINING_CORPUS: list[tuple[str, str]] = [
    # Food (36)
    ("Highlands Coffee sáng", "Food"),
    ("Highlands Coffee chạy deadline", "Food"),
    ("Highlands Coffee học nhóm", "Food"),
    ("Phúc Long Tea cùng bạn", "Food"),
    ("Phúc Long trà đào buổi chiều", "Food"),
    ("Katinat Coffee & Tea", "Food"),
    ("Katinat cà phê sữa đá", "Food"),
    ("Starbucks cà phê làm việc", "Food"),
    ("Cơm tấm sườn bì chả", "Food"),
    ("Cơm tấm trưa gần trường", "Food"),
    ("Cơm văn phòng bữa trưa", "Food"),
    ("Cơm gà xối mỡ tối", "Food"),
    ("Phở bò tái bữa sáng", "Food"),
    ("Phở gà ăn sáng", "Food"),
    ("Bún bò Huế bữa trưa", "Food"),
    ("Bún đậu mắm tôm tối", "Food"),
    ("Bánh mì thịt nướng sáng", "Food"),
    ("GrabFood gà rán bữa tối", "Food"),
    ("GrabFood pizza nhóm dự án", "Food"),
    ("GrabFood bún chả trưa", "Food"),
    ("GrabFood cơm sườn tối", "Food"),
    ("ShopeeFood trà sữa Mixue", "Food"),
    ("ShopeeFood cơm gà trưa", "Food"),
    ("ShopeeFood đặt trà sữa", "Food"),
    ("ShopeeFood bánh tráng trộn", "Food"),
    ("Lẩu Haidilao sinh nhật bạn", "Food"),
    ("MoMo thanh toán lẩu băng chuyền", "Food"),
    ("MoMo thanh toán ăn nướng BBQ", "Food"),
    ("MoMo thanh toán quán ăn trưa", "Food"),
    ("Siêu thị WinMart mua đồ ăn tuần", "Food"),
    ("WinMart mua trái cây và sữa", "Food"),
    ("Siêu thị Circle K đồ ăn vặt", "Food"),
    ("Circle K mua nước suối bánh mì", "Food"),
    ("GS25 đồ ăn nhanh buổi tối", "Food"),
    ("Trà sữa Gong Cha cuối tuần", "Food"),
    ("Trà sữa Mixue kem tươi", "Food"),
    # Shopping (36)
    ("Shopee đơn hàng đồ gia dụng", "Shopping"),
    ("Shopee phụ kiện laptop chuột", "Shopping"),
    ("Shopee 10.10 giày sneaker", "Shopping"),
    ("Shopee 11.11 tai nghe Sony chống ồn", "Shopping"),
    ("Shopee 11.11 combo đồ skincare", "Shopping"),
    ("Shopee mua balo đi học", "Shopping"),
    ("Shopee mua đèn bàn học", "Shopping"),
    ("Shopee dây sạc và ốp lưng", "Shopping"),
    ("Shopee quần áo thời trang", "Shopping"),
    ("Shopee mua bàn phím cơ", "Shopping"),
    ("TikTok Shop áo thun basic", "Shopping"),
    ("TikTok Shop skincare dưỡng ẩm", "Shopping"),
    ("TikTok Shop áo khoác mùa đông", "Shopping"),
    ("TikTok Shop son dưỡng mỹ phẩm", "Shopping"),
    ("TikTok Shop giày dép sale", "Shopping"),
    ("TikTok Shop phụ kiện điện thoại", "Shopping"),
    ("Uniqlo mua sơ mi đi phỏng vấn", "Shopping"),
    ("Uniqlo mua áo thun quần tây", "Shopping"),
    ("Lazada đặt mua bàn phím chuột", "Shopping"),
    ("Lazada đơn hàng gia dụng", "Shopping"),
    ("Tiki mua tai nghe phụ kiện", "Shopping"),
    ("Tiki mua đồ dùng cá nhân", "Shopping"),
    ("Zara mua quần jean áo sơ mi", "Shopping"),
    ("H&M mua áo khoác thời trang", "Shopping"),
    ("CellphoneS mua sạc dự phòng", "Shopping"),
    ("CellphoneS mua tai nghe cáp sạc", "Shopping"),
    ("Thế Giới Di Động mua phụ kiện", "Shopping"),
    ("Guardian mua sữa rửa mặt skincare", "Shopping"),
    ("Guardian kem chống nắng mỹ phẩm", "Shopping"),
    ("Hasaki mỹ phẩm tẩy trang skincare", "Shopping"),
    ("Hasaki sữa rửa mặt dưỡng ẩm", "Shopping"),
    ("Mua giày sneaker Adidas sale", "Shopping"),
    ("Mua túi xách balo thời trang", "Shopping"),
    ("Sendo đơn hàng đồ gia dụng", "Shopping"),
    ("Mua quần áo mới đi làm", "Shopping"),
    ("Mua mỹ phẩm skincare cuối tháng", "Shopping"),
    # Transport (36)
    ("GrabBike đi làm sáng", "Transport"),
    ("GrabBike đi học tối", "Transport"),
    ("GrabBike đi thực tập", "Transport"),
    ("GrabBike về trọ trời mưa", "Transport"),
    ("GrabBike đi họp hackathon", "Transport"),
    ("GrabCar ra sân bay", "Transport"),
    ("GrabCar đi gặp khách hàng", "Transport"),
    ("Xanh SM đi gặp nhóm", "Transport"),
    ("Xanh SM đi hội thảo", "Transport"),
    ("Xanh SM đi thuyết trình", "Transport"),
    ("Xanh SM đi thực tập trời mưa", "Transport"),
    ("BeBike di chuyển đến trường", "Transport"),
    ("BeBike đi làm buổi sáng", "Transport"),
    ("Gojek đặt xe đi làm", "Transport"),
    ("Gojek di chuyển trong thành phố", "Transport"),
    ("Đổ xăng Petrolimex", "Transport"),
    ("Đổ xăng Petrolimex A95", "Transport"),
    ("Đổ xăng xe máy đầy bình", "Transport"),
    ("Đổ xăng đi học hàng tuần", "Transport"),
    ("Vé xe buýt tháng sinh viên", "Transport"),
    ("Vé xe buýt đi học", "Transport"),
    ("Vé tàu điện Metro đi làm", "Transport"),
    ("Vé tàu Metro tháng", "Transport"),
    ("Tiền gửi xe máy trường đại học", "Transport"),
    ("Gửi xe máy trung tâm thương mại", "Transport"),
    ("Phí gửi xe tháng tại phòng trọ", "Transport"),
    ("Gửi xe đi làm hàng ngày", "Transport"),
    ("Thay nhớt bảo dưỡng xe máy", "Transport"),
    ("Bảo dưỡng sửa xe máy định kỳ", "Transport"),
    ("Rửa xe máy cuối tuần", "Transport"),
    ("Vá lốp xe máy dọc đường", "Transport"),
    ("Vé xe khách về quê nghỉ lễ", "Transport"),
    ("Vé xe Phương Trang về quê", "Transport"),
    ("Taxi Mai Linh đi công việc", "Transport"),
    ("Taxi công nghệ ra bến xe", "Transport"),
    ("Đặt xe máy công nghệ về nhà", "Transport"),
    # Bills (36)
    ("Tiền thuê phòng trọ", "Bills"),
    ("Tiền thuê phòng trọ tháng này", "Bills"),
    ("Chuyển khoản tiền thuê nhà trọ", "Bills"),
    ("Thanh toán tiền trọ chủ nhà", "Bills"),
    ("Tiền điện nước phòng trọ", "Bills"),
    ("Thanh toán tiền điện nước tháng", "Bills"),
    ("Hóa đơn tiền điện EVN", "Bills"),
    ("Thanh toán hóa đơn điện EVN", "Bills"),
    ("Đóng tiền điện máy lạnh phòng trọ", "Bills"),
    ("Hóa đơn tiền nước sinh hoạt", "Bills"),
    ("Thanh toán tiền nước phòng trọ", "Bills"),
    ("Internet FPT hàng tháng", "Bills"),
    ("Cước internet FPT tháng", "Bills"),
    ("Thanh toán hóa đơn wifi FPT", "Bills"),
    ("Cước wifi VNPT phòng trọ", "Bills"),
    ("Thanh toán internet VNPT", "Bills"),
    ("Cước internet Viettel cáp quang", "Bills"),
    ("Cước 4G Viettel", "Bills"),
    ("Gia hạn gói cước 4G Viettel", "Bills"),
    ("Nạp gói data 5G Viettel", "Bills"),
    ("Cước 4G Mobifone hàng tháng", "Bills"),
    ("Nạp gói data 4G Mobifone", "Bills"),
    ("Cước điện thoại trả sau Vinaphone", "Bills"),
    ("Thanh toán cước di động Vinaphone", "Bills"),
    ("Phí dịch vụ quản lý phòng trọ", "Bills"),
    ("Tiền rác vệ sinh khu trọ", "Bills"),
    ("Hóa đơn tiền rác hàng tháng", "Bills"),
    ("Thanh toán hóa đơn điện qua MoMo", "Bills"),
    ("Thanh toán hóa đơn nước qua MoMo", "Bills"),
    ("Đóng tiền wifi chung phòng trọ", "Bills"),
    ("Hóa đơn tiền gas phòng trọ", "Bills"),
    ("Chi phí điện nước cố định tháng", "Bills"),
    ("Thanh toán hóa đơn truyền hình cáp", "Bills"),
    ("Cước thuê bao internet gia đình", "Bills"),
    ("Hóa đơn tiện ích điện nước wifi", "Bills"),
    ("Đóng tiền phòng và điện nước", "Bills"),
    # Entertainment (36)
    ("Spotify Premium", "Entertainment"),
    ("Gia hạn gói Spotify Premium", "Entertainment"),
    ("Spotify gói sinh viên hàng tháng", "Entertainment"),
    ("Netflix Standard", "Entertainment"),
    ("Gia hạn gói Netflix hàng tháng", "Entertainment"),
    ("Netflix chia sẻ gói xem phim", "Entertainment"),
    ("iCloud+ 50GB", "Entertainment"),
    ("Gia hạn dung lượng iCloud+ Apple", "Entertainment"),
    ("YouTube Premium gia hạn tháng", "Entertainment"),
    ("Đăng ký YouTube Premium", "Entertainment"),
    ("Apple Music gói sinh viên", "Entertainment"),
    ("CGV Cinemas xem phim cuối tuần", "Entertainment"),
    ("CGV Cinemas vé xem phim và bắp nước", "Entertainment"),
    ("CGV đặt vé phim chiếu rạp", "Entertainment"),
    ("Lotte Cinema vé xem phim", "Entertainment"),
    ("Galaxy Cinema xem phim cuối tuần", "Entertainment"),
    ("Beta Cinemas vé phim sinh viên", "Entertainment"),
    ("Bida cuối tuần cùng bạn", "Entertainment"),
    ("Chơi bida giải trí tối", "Entertainment"),
    ("Boardgame café cùng nhóm", "Entertainment"),
    ("Chơi boardgame cuối tuần", "Entertainment"),
    ("Karaoke sinh nhật bạn đại học", "Entertainment"),
    ("Đi hát karaoke cùng nhóm bạn", "Entertainment"),
    ("Mua game trên Steam sale", "Entertainment"),
    ("Steam mua game giải trí", "Entertainment"),
    ("Nạp thẻ game cuối tuần", "Entertainment"),
    ("Chơi net phòng máy giải trí", "Entertainment"),
    ("Vé concert ca nhạc cuối tuần", "Entertainment"),
    ("Vé liveshow âm nhạc giải trí", "Entertainment"),
    ("Công viên giải trí cuối tuần", "Entertainment"),
    ("Thuê sân cầu lông chơi thể thao", "Entertainment"),
    ("Bowling giải trí cuối tuần", "Entertainment"),
    ("Gói xem phim FPT Play tháng", "Entertainment"),
    ("Đăng ký VieON giải trí", "Entertainment"),
    ("Vé triển lãm nghệ thuật", "Entertainment"),
    ("Du lịch cắm trại cuối tuần", "Entertainment"),
    # Other (36)
    ("Nhà sách Fahasa mua giáo trình", "Other"),
    ("Fahasa mua sổ bút văn phòng phẩm", "Other"),
    ("Mua sách giáo trình đại học", "Other"),
    ("Mua sách tiếng Anh luyện thi IELTS", "Other"),
    ("Đóng lệ phí thi chứng chỉ TOEIC", "Other"),
    ("Lệ phí thi chứng chỉ tiếng Anh", "Other"),
    ("Đóng học phí học kỳ đại học", "Other"),
    ("Học phí khóa học online Coursera", "Other"),
    ("In ấn tài liệu photocopy bài tập", "Other"),
    ("Photocopy giáo trình trước kỳ thi", "Other"),
    ("Cắt tóc 30Shine", "Other"),
    ("Cắt tóc 30Shine cuối tháng", "Other"),
    ("Cắt tóc nam tiệm gần trọ", "Other"),
    ("Nhà thuốc Long Châu mua thuốc cảm", "Other"),
    ("Nhà thuốc Long Châu mua vitamin", "Other"),
    ("Long Châu mua khẩu trang thuốc nhỏ mắt", "Other"),
    ("Nhà thuốc Pharmacity mua thuốc", "Other"),
    ("Pharmacity mua vitamin sức khỏe", "Other"),
    ("Khám răng nha khoa định kỳ", "Other"),
    ("Khám sức khỏe tổng quát bệnh viện", "Other"),
    ("Chi phí khám bệnh phòng khám", "Other"),
    ("Quà tặng sinh nhật bạn thân", "Other"),
    ("Mua quà sinh nhật tặng bạn", "Other"),
    ("Mua hoa quà tặng thầy cô", "Other"),
    ("Mừng cưới anh chị cùng câu lạc bộ", "Other"),
    ("Đóng quỹ lớp và hoạt động CLB", "Other"),
    ("Đóng quỹ nhóm dự án sinh viên", "Other"),
    ("Giặt ủi quần áo tiệm gần trọ", "Other"),
    ("Giặt sấy chăn màn phòng trọ", "Other"),
    ("Ủng hộ quyên góp từ thiện", "Other"),
    ("Phí làm lại thẻ sinh viên", "Other"),
    ("Phí chuyển khoản ngân hàng", "Other"),
    ("Mua văn phòng phẩm sổ bút", "Other"),
    ("Sửa màn hình laptop bảo hành", "Other"),
    ("Vệ sinh bảo dưỡng laptop", "Other"),
    ("Gửi bưu phẩm chuyển phát nhanh về quê", "Other"),
]

HIGH_PRECISION_RULES: list[tuple[str, list[str]]] = [
    ("Food", ["grabfood", "shopeefood", "befood", "baemin", "highlands", "phúc long", "phuc long", "katinat", "mixue", "cơm ", "phở ", "bún ", "lẩu ", "winmart", "circle k"]),
    ("Bills", ["thuê phòng", "thue phong", "tiền trọ", "tiền điện", "điện nước", "internet fpt", "viettel", "mobifone", "vinaphone", "4g", "5g", "evn"]),
    ("Entertainment", ["spotify", "netflix", "icloud", "youtube premium", "cgv", "lotte cinema", "galaxy cinema", "boardgame", "bida", "karaoke", "steam"]),
    ("Transport", ["grabbike", "grabcar", "xanh sm", "petrolimex", "đổ xăng", "xe buýt", "metro", "gửi xe"]),
    ("Shopping", ["shopee", "tiktok shop", "lazada", "tiki", "uniqlo", "zara", "h&m", "skincare"]),
    ("Other", ["fahasa", "giáo trình", "học phí", "lệ phí thi", "30shine", "cắt tóc", "long châu", "pharmacity", "nhà thuốc", "quà tặng"]),
]


def _build_vectorizer() -> FeatureUnion:
    return FeatureUnion(
        [
            ("word_tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)),
            ("char_tfidf", TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ]
    )


def _build_logreg_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("features", _build_vectorizer()),
            ("clf", LogisticRegression(max_iter=1000, C=4.0, random_state=42)),
        ]
    )


def _build_rf_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("features", _build_vectorizer()),
            ("clf", RandomForestClassifier(n_estimators=200, random_state=42)),
        ]
    )


@lru_cache(maxsize=1)
def get_trained_classifier() -> Pipeline:
    """Train and cache the Scikit-learn TF-IDF + LogisticRegression classifier."""
    texts = [t for t, _ in TRAINING_CORPUS]
    labels = [y for _, y in TRAINING_CORPUS]
    pipe = _build_logreg_pipeline()
    pipe.fit(texts, labels)
    return pipe


def predict_single_transaction(description: str, tx_type: str = "expense") -> tuple[str, float, str]:
    """Predict category, confidence score (0-1), and method for one transaction."""
    if tx_type == "income":
        return "Income", 1.0, "Rule (Income)"

    text_lower = f" {str(description).lower().strip()} "
    clf = get_trained_classifier()
    probs = clf.predict_proba([str(description)])[0]
    classes = list(clf.classes_)
    best_idx = int(np.argmax(probs))
    ml_label = classes[best_idx]
    ml_conf = float(probs[best_idx])

    for rule_cat, keywords in HIGH_PRECISION_RULES:
        if any(kw in text_lower for kw in keywords):
            if rule_cat == ml_label:
                return ml_label, min(0.99, max(ml_conf, 0.94)), "ML + Rule Agreement"
            return rule_cat, max(0.92, ml_conf), "Hybrid Rule Override"

    return ml_label, round(ml_conf, 3), "Scikit-learn ML"


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing/blank `category` cells using the trained Scikit-learn ML + Hybrid pipeline."""
    out = df.copy()
    if "is_auto_categorized" not in out.columns:
        out["is_auto_categorized"] = (out["category"].fillna("").astype(str).str.strip() == "") & (out["type"] == "expense")
    if "category_confidence" not in out.columns:
        out["category_confidence"] = 1.0
    if "categorization_method" not in out.columns:
        out["categorization_method"] = "User Provided"

    out.loc[out["type"] == "income", "category"] = "Income"
    out.loc[out["type"] == "income", "category_confidence"] = 1.0

    blank_mask = (out["type"] == "expense") & (out["category"].fillna("").astype(str).str.strip() == "")
    if blank_mask.any():
        preds, confs, methods = [], [], []
        for desc, tx_type in zip(out.loc[blank_mask, "description"], out.loc[blank_mask, "type"]):
            cat, conf, method = predict_single_transaction(desc, tx_type)
            preds.append(cat)
            confs.append(conf)
            methods.append(method)
        out.loc[blank_mask, "category"] = preds
        out.loc[blank_mask, "category_confidence"] = confs
        out.loc[blank_mask, "categorization_method"] = methods
        out.loc[blank_mask, "is_auto_categorized"] = True

    return out


@lru_cache(maxsize=1)
def evaluate_categorization_model() -> dict[str, Any]:
    """Run 5-fold Stratified Cross-Validation benchmarking Logistic Regression vs Random Forest."""
    texts = [t for t, _ in TRAINING_CORPUS]
    labels = [y for _, y in TRAINING_CORPUS]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    lr_preds = cross_val_predict(_build_logreg_pipeline(), texts, labels, cv=cv)
    rf_preds = cross_val_predict(_build_rf_pipeline(), texts, labels, cv=cv)

    lr_acc = float(accuracy_score(labels, lr_preds))
    lr_f1 = float(f1_score(labels, lr_preds, average="macro"))
    rf_acc = float(accuracy_score(labels, rf_preds))
    rf_f1 = float(f1_score(labels, rf_preds, average="macro"))

    report_dict = classification_report(labels, lr_preds, labels=EXPENSE_CLASSES, output_dict=True, zero_division=0)
    per_class = [
        {
            "category": cls,
            "precision": round(float(report_dict[cls]["precision"]) * 100, 1),
            "recall": round(float(report_dict[cls]["recall"]) * 100, 1),
            "f1_score": round(float(report_dict[cls]["f1-score"]) * 100, 1),
            "support": int(report_dict[cls]["support"]),
        }
        for cls in EXPENSE_CLASSES
    ]
    cm = confusion_matrix(labels, lr_preds, labels=EXPENSE_CLASSES).tolist()

    return {
        "active_model": "TF-IDF (Word + Char N-gram) + Logistic Regression",
        "corpus_size": len(TRAINING_CORPUS),
        "cv_folds": 5,
        "accuracy_pct": round(lr_acc * 100, 1),
        "macro_f1_pct": round(lr_f1 * 100, 1),
        "rf_comparison_accuracy_pct": round(rf_acc * 100, 1),
        "rf_comparison_f1_pct": round(rf_f1 * 100, 1),
        "per_class": per_class,
        "confusion_matrix": cm,
        "classes": EXPENSE_CLASSES,
    }
