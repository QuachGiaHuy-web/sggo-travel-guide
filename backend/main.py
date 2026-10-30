# -*- coding: utf-8 -*-
"""
main.py - BACKEND REST API CHO DỰ ÁN SGGO! TRAVEL GUIDE
Môn học: Công nghệ Phần mềm (COMP1044)

Kiến trúc rõ ràng, dễ hiểu:
1. Module CSDL: SQLite (qua backend.database)
2. Module AI & GPS: Google Gemini AI + OpenStreetMap Nominatim Geocoding
3. Module Thuật toán: Nearest Neighbor (Haversine Distance)
4. Phân quyền: Khách vãng lai, Thành viên và Quản trị viên (Admin)
"""

import os
import json
import math
import re
import unicodedata
import urllib.request
import urllib.parse
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

from backend.database import (
    init_db, authenticate_user, register_user,
    get_all_places, get_place_by_id, add_place, update_place, delete_place,
    generate_sample_csv, import_csv_data,
    get_connection, get_all_users, update_user_role, delete_user,
    toggle_hide_place, save_itinerary, get_import_logs,
    get_all_tags, add_tag, update_tag, delete_tag, toggle_tag_active
)
import datetime

# Tự động đọc file .env
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

# Khởi tạo CSDL SQLite khi server bật
init_db()

app = FastAPI(title="SGGo! Travel Guide API", version="2.0.0")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Gemini AI Client
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ai_client = None
if GEMINI_KEY:
    try:
        from google import genai
        ai_client = genai.Client(api_key=GEMINI_KEY)
    except Exception:
        ai_client = None

# ==============================================================================
# PYDANTIC DATA MODELS
# ==============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str

class QuickRecommendRequest(BaseModel):
    category: Optional[str] = "all"      # 'an_uong', 'di_choi'
    context: Optional[str] = "all"       # 'di_1_minh', 'nguoi_yeu', 'ban_be', 'gia_dinh'
    price_level: Optional[str] = "all"   # 'under_50k', '50k_100k', '100k_250k', 'above_250k', 'custom', 'all'
    custom_budget: Optional[int] = None
    offset: Optional[int] = 0
    client_time: Optional[str] = None    # Giờ kiểm tra (HH:MM) để lọc quán mở/đóng

class UserRoleUpdate(BaseModel):
    role: str

class ExtractGmapsRequest(BaseModel):
    url_or_query: str

class ItineraryRequest(BaseModel):
    start_location: str
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    free_time: str                       # Giờ rảnh: '14:00 - 18:30', '19:00 - 22:30', etc.
    companion: Optional[str] = "ban_be"  # 'di_1_minh', 'nguoi_yeu', 'ban_be', 'gia_dinh'
    purpose: Optional[str] = "ca_hai"    # 'an_uong', 'di_choi', 'ca_hai'
    takenote: Optional[str] = ""         # Ghi chú / Loại trừ địa điểm
    context: Optional[str] = ""          # Giữ tương thích ngược
    budget: Optional[str] = "100k_250k"
    budget_level: Optional[str] = "100k_250k"
    target_budget: Optional[int] = 250000
    shuffle_seed: Optional[int] = 0      # Dùng cho G6-FR06: Xáo trộn / Đổi phương án khác
    ai_model: Optional[str] = "gemini-3.8-flash"

class PlaceModel(BaseModel):
    name: str
    category: str
    address: str
    district: Optional[str] = "Quận 5"
    lat: Optional[float] = 10.7550
    lon: Optional[float] = 106.6650
    open_time: Optional[str] = "08:00"
    close_time: Optional[str] = "22:00"
    min_price: Optional[int] = 30000
    max_price: Optional[int] = 100000
    rating: Optional[float] = 4.5
    reviews_count: Optional[int] = 100
    peak_hours: Optional[str] = "18:00 - 20:00"
    best_review: Optional[str] = ""
    worst_review: Optional[str] = ""
    image_url: Optional[str] = None
    tags: Optional[str] = "nhom_ban"
    is_verified: Optional[int] = 1
    is_verified_review: Optional[int] = 1
    is_admin_choice: Optional[int] = 0
    is_hidden: Optional[int] = 0
    price_display: Optional[str] = None
    hours_display: Optional[str] = None

# ==============================================================================
# THUẬT TOÁN ĐỊNH TUYẾN & GPS (HAVERSINE NEAREST NEIGHBOR)
# ==============================================================================

def remove_accent(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để tìm kiếm không phân biệt dấu"""
    text = unicodedata.normalize('NFD', text)
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn').lower()

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách đường tròn lớn giữa 2 tọa độ GPS (km)"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def resolve_start_coords(location_str: str):
    """
    Geocoding điểm xuất phát:
    1. Ưu tiên tra cứu nhanh các địa danh/trường học/chợ nổi tiếng tại Quận 5 (0ms).
    2. Nếu không có trong danh mục nhanh -> Gọi OpenStreetMap Nominatim.
    3. Nếu không tìm thấy hoặc mất mạng -> Fallback về tọa độ trung tâm Quận 5.
    """
    loc_clean = location_str.strip()
    loc_norm = remove_accent(loc_clean)

    # 1. Bảng toạ độ tức thì cho các địa danh tiêu biểu tại Quận 5
    landmarks = {
        "su pham": (10.7601, 106.6823),
        "280 an duong vuong": (10.7601, 106.6823),
        "an duong vuong": (10.7601, 106.6823),
        "an dong": (10.7573, 106.6713),
        "cho an dong": (10.7573, 106.6713),
        "binh tay": (10.7497, 106.6515),
        "cho binh tay": (10.7497, 106.6515),
        "cho lon": (10.7535, 106.6580),
        "thuan kieu": (10.7554, 106.6577),
        "cho ray": (10.7577, 106.6596),
        "benh vien cho ray": (10.7577, 106.6596),
        "y duoc": (10.7562, 106.6589),
        "dai hoc y duoc": (10.7562, 106.6589),
        "van lang": (10.7585, 106.6705),
        "cong vien van lang": (10.7585, 106.6705),
        "hung vuong": (10.7570, 106.6625),
        "dai the gioi": (10.7530, 106.6690),
        "sai gon": (10.7554, 106.6577)
    }
    for k, coords in landmarks.items():
        if k in loc_norm:
            return coords

    # 2. Gọi Nominatim nếu là địa chỉ lạ
    try:
        query = f"{loc_clean}, Ho Chi Minh City, Vietnam"
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            "q": query, "format": "json", "limit": 1
        })
        req = urllib.request.Request(url, headers={"User-Agent": "SGGo-Travel-Guide-D5/2.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass

    # 3. Mặc định: Tâm Quận 5 (Khu vực Thuận Kiều Plaza / Hồng Bàng)
    return 10.7554, 106.6577

def optimize_route_nearest_neighbor(start_coords, candidates, max_stops=3):
    """Thuật toán láng giềng gần nhất (Nearest Neighbor) chọn 3 trạm liên hoàn thuận đường"""
    current_lat, current_lon = start_coords
    unvisited = list(candidates)
    route = []

    for _ in range(min(max_stops, len(candidates))):
        nearest_node = None
        min_dist = float('inf')

        for place in unvisited:
            p_lat = place.get("lat") or 10.7550
            p_lon = place.get("lon") or 106.6650
            dist = calculate_haversine_distance(current_lat, current_lon, p_lat, p_lon)
            if dist < min_dist:
                min_dist = dist
                nearest_node = place

        if nearest_node:
            dist_km = round(min_dist, 2)
            travel_min = max(3, int(round(dist_km * 3.5))) # Ước tính 3.5 phút/km xe máy Sài Gòn
            node_copy = dict(nearest_node)
            node_copy["dist_km"] = dist_km
            node_copy["travel_minutes"] = travel_min
            route.append(node_copy)
            current_lat, current_lon = nearest_node["lat"], nearest_node["lon"]
            unvisited.remove(nearest_node)

    return route

# ==============================================================================
# CÁC API XÁC THỰC TÀI KHOẢN (AUTH)
# ==============================================================================

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")
    return {"status": "ok", "user": user}

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    user = register_user(req.username, req.password, req.full_name)
    if not user:
        raise HTTPException(status_code=400, detail="Tên tài khoản này đã có người sử dụng!")
    return {"status": "ok", "user": user}

# ==============================================================================
# CÁC API ĐỊA ĐIỂM (PLACES & SEARCH TỪ A ĐẾN Z)
# ==============================================================================

@app.get("/api/places")
def get_places(category: Optional[str] = None, tag: Optional[str] = None, 
               min_price: Optional[int] = None, max_price: Optional[int] = None,
               min_rating: Optional[float] = None, search: Optional[str] = None,
               only_verified: Optional[bool] = True, include_hidden: Optional[bool] = False):
    return get_all_places(category=category, context_tag=tag, min_budget=min_price, 
                          max_budget=max_price, min_rating=min_rating, search=search, 
                          only_verified=only_verified, include_hidden=include_hidden)

@app.get("/api/places/{place_id}")
def get_place(place_id: int):
    place = get_place_by_id(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm này.")
    return place

# ==============================================================================
# API GỢI Ý NHANH (QUICK RECOMMENDATION - 5 MỨC NGÂN SÁCH & TỰ NHẬP)
# ==============================================================================

def parse_place_tiers(place):
    """
    Bóc tách cấu trúc 2-Tier:
    - Nếu chuỗi có định dạng tier1:...|tier2:...: bóc tách chính xác từng Tier.
    - Nếu chuỗi dạng cũ phân tách dấu phẩy (tag1,tag2,tag3,tag4): 2 tag đầu là Tier 1, còn lại là Tier 2.
    """
    tags_str = (place.get("tags") or "").strip()
    if not tags_str:
        return [], []
    if "tier1:" in tags_str or "tier2:" in tags_str:
        parts = tags_str.split("|")
        t1, t2 = [], []
        for p in parts:
            p = p.strip()
            if p.startswith("tier1:"):
                t1 = [x.strip() for x in p.replace("tier1:", "").split(",") if x.strip()]
            elif p.startswith("tier2:"):
                t2 = [x.strip() for x in p.replace("tier2:", "").split(",") if x.strip()]
        return t1, t2
    else:
        all_tags = [x.strip() for x in tags_str.split(",") if x.strip()]
        return all_tags[:2], all_tags[2:]


def get_companion_tier_score(place, mapped_tag):
    """
    Mô hình Phân Tầng 2 Bậc (2-Tier Fit Model):
    - Tier 1 (Cốt lõi - Phù hợp xuất sắc): +20.0 điểm cho MỌI tag thuộc Tier 1 (CÙNG TIER THÌ CÙNG ĐIỂM)
    - Tier 2 (Khả dụng / Thứ cấp): +12.0 điểm cho MỌI tag thuộc Tier 2 (CÙNG TIER THÌ CÙNG ĐIỂM)
    - Không có tag: -10.0 điểm
    """
    if not mapped_tag:
        return 0.0, None
    t1, t2 = parse_place_tiers(place)
    if mapped_tag in t1:
        return 20.0, 1
    elif mapped_tag in t2:
        return 12.0, 2
    else:
        return -10.0, None


@app.post("/api/quick-recommend")
def quick_recommend(req: QuickRecommendRequest):
    """
    Thuật toán phân tích ma trận đa chiều & Chấm điểm độ phù hợp (Smart Scoring):
    1. Lọc thể loại (category): Ẩm thực hoặc Vui chơi
    2. Điểm tương thích đồng hành (context): đi 1 mình, cặp đôi, nhóm bạn, gia đình (chuẩn hóa 2-Tier)
    3. Điểm khớp ngân sách (budget): <50k, 50k-100k, 100k-250k, >250k hoặc số tiền tự nhập
    4. Trọng số uy tín (rating, reviews)
    5. Hỗ trợ offset xoay vòng (Đổi gợi ý khác) không bao giờ bị trùng lặp cứng nhắc
    """
    all_places = get_all_places(category=req.category, include_hidden=False)
    if not all_places:
        all_places = get_all_places(include_hidden=False)

    tag_mapping = {
        "di_1_minh": "di_1_minh",
        "nguoi_yeu": "hen_ho",
        "ban_be": "nhom_ban",
        "gia_dinh": "gia_dinh"
    }
    mapped_tag = tag_mapping.get(req.context, None)

    scored_places = []
    for p in all_places:
        score = 0.0
        p_dict = dict(p)

        # 1. Khớp Category
        if req.category and req.category != "all" and p.get("category") != req.category:
            continue

        # 2. Khớp Context (Đồng hành) - Mô hình 2-Tier Chuẩn Xác (Cùng Tier thì Cùng Điểm)
        tier_pts, fit_tier = get_companion_tier_score(p, mapped_tag)
        score += tier_pts
        p_dict["fit_tier"] = fit_tier

        # 2.5 Kiểm tra trạng thái mở cửa (Business Rule 2: không gợi ý quán đóng cửa)
        check_t = req.client_time
        if not check_t:
            now_vn = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
            check_t = now_vn.strftime("%H:%M")
        is_open_now = is_place_open_at_time(p, check_t)
        p_dict["is_currently_open"] = is_open_now
        if is_open_now:
            score += 15.0
        else:
            score -= 40.0  # Ưu tiên dứt điểm các quán đang mở cửa lên trước

        # 3. Khớp Ngân sách (Loại trừ tuyệt đối các quán vi phạm giới hạn ngân sách)
        min_p = p.get("min_price", 0)
        max_p = p.get("max_price", 0)
        avg_p = (min_p + max_p) / 2.0

        if req.price_level == "free":
            # Khi chọn Miễn phí (0đ): BẮT BUỘC giá phải là 0đ (loại bỏ tuyệt đối quán có thu phí)
            if not (min_p == 0 and max_p == 0):
                continue
            score += 35.0
        elif p.get("category") == "di_choi" and min_p == 0 and max_p == 0:
            if req.price_level == "under_50k":
                score += 20.0
            elif req.price_level == "50k_100k":
                score += 10.0
            else:
                score += 5.0
        else:
            if req.price_level == "under_50k":
                # Dưới 50k: Quán phải có giá tối thiểu <= 65k (loại bỏ dứt điểm các quán đắt tiền 100k, 200k)
                if min_p > 65000:
                    continue
                if max_p <= 55000:
                    score += 25.0
                else:
                    score += 15.0
            elif req.price_level == "50k_100k":
                # 50k - 100k: Quán trong khoảng hợp lý [40k, 125k]
                if min_p > 125000 or (max_p > 0 and max_p < 40000):
                    continue
                if 45000 <= avg_p <= 110000:
                    score += 25.0
                else:
                    score += 15.0
            elif req.price_level == "100k_250k":
                # 100k - 250k: Quán trong khoảng [90k, 280k]
                if min_p > 280000 or (max_p > 0 and max_p < 85000):
                    continue
                if 95000 <= avg_p <= 260000:
                    score += 25.0
                else:
                    score += 15.0
            elif req.price_level == "above_250k":
                # Trên 250k: Trải nghiệm cao cấp
                if max_p > 0 and max_p < 150000:
                    continue
                if max_p >= 250000:
                    score += 25.0
                else:
                    score += 15.0
            elif req.price_level == "custom" and req.custom_budget and req.custom_budget > 0:
                cb = req.custom_budget
                if min_p > cb * 1.3:
                    continue
                ratio = min(avg_p, cb) / max(avg_p, cb, 1)
                score += 25.0 * ratio

        # 4. Trọng số Đánh giá (Rating & Reviews)
        rating = float(p.get("rating", 4.0))
        reviews_count = int(p.get("reviews_count", 0))

        # Điểm số sao: Chuẩn hóa tách mốc trung bình 4.0 (Mean-Centering)
        rating_score = (rating - 4.0) * 4.0

        # Điểm độ uy tín cộng đồng: Biến đổi Logarithmic Scaling log10(reviews + 1) * 2.0
        if rating >= 4.0:
            review_score = math.log10(reviews_count + 1) * 2.0
        else:
            review_score = -math.log10(reviews_count + 1) * 1.0

        score += (rating_score + review_score)
        scored_places.append((score, p_dict))

    # Xử lý trường hợp: Người dùng chọn Ẩm thực nhưng lại chọn Miễn phí (0đ).
    # Thực tế Sài Gòn không có quán ăn miễn phí 0đ, tự động chuyển hướng tìm các điểm tham quan/check-in 0đ!
    if not scored_places and req.price_level == "free":
        free_places = [p for p in get_all_places(category="di_choi", include_hidden=False) if p.get("min_price", 0) == 0 and p.get("max_price", 0) == 0]
        for p in free_places:
            p_dict = dict(p)
            tier_pts, fit_tier = get_companion_tier_score(p, mapped_tag)
            p_dict["fit_tier"] = fit_tier
            p_dict["free_fallback_notice"] = "Sài Gòn không có quán ăn miễn phí (0đ). SGGo đã gợi ý các điểm đến tham quan & check-in 0đ phù hợp nhất cho bạn!"
            rating = float(p.get("rating", 4.0))
            reviews_count = int(p.get("reviews_count", 0))
            r_score = (rating - 4.0) * 4.0 + (math.log10(reviews_count + 1) * 2.0 if rating >= 4.0 else -math.log10(reviews_count + 1))
            scored_places.append((tier_pts + 35.0 + r_score, p_dict))

    # Sắp xếp theo điểm phù hợp giảm dần
    scored_places.sort(key=lambda x: x[0], reverse=True)
    sorted_places = [item[1] for item in scored_places]

    if not sorted_places:
        sorted_places = all_places

    # Xử lý xoay vòng gợi ý (offset) để người dùng bấm "Đổi 3 quán khác"
    offset = req.offset or 0
    if offset >= len(sorted_places):
        offset = 0

    results = sorted_places[offset : offset + 3]
    if len(results) < 3 and len(sorted_places) >= 3:
        results.extend(sorted_places[: 3 - len(results)])

    return results

# ==============================================================================
# API LẬP LỘ TRÌNH THÔNG MINH (RULE-BASED + HEURISTIC TSP + GEMINI AI EXPLANATION)
# ==============================================================================

def parse_free_time_minutes(free_time_str: str) -> int:
    """Tính tổng số phút rảnh từ chuỗi thời gian (VD: '14:00 - 18:30' -> 270 phút)"""
    if not free_time_str:
        return 240
    parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', free_time_str)
    if len(parts) >= 2:
        h1, m1 = int(parts[0][0]), int(parts[0][1] or 0)
        h2, m2 = int(parts[1][0]), int(parts[1][1] or 0)
        start_m = h1 * 60 + m1
        end_m = h2 * 60 + m2
        if end_m < start_m:
            end_m += 24 * 60
        return max(15, end_m - start_m)
    h_match = re.search(r'(\d+)\s*(tiếng|giờ|h)', free_time_str, re.IGNORECASE)
    if h_match:
        return int(h_match.group(1)) * 60
    return 240

def parse_target_budget_amount(req: ItineraryRequest) -> int:
    """Xác định ngân sách mục tiêu dạng số nguyên (VNĐ)"""
    if req.target_budget and req.target_budget > 0:
        return req.target_budget
    lvl = req.budget_level or req.budget or "100k_250k"
    if lvl == "free":
        return 0
    elif lvl == "under_100k":
        return 100000
    elif lvl == "100k_250k":
        return 250000
    elif lvl == "above_250k":
        return 500000
    return 250000

def is_place_open_at_time(p: dict, check_time_str: str) -> bool:
    """Kiểm tra quán có đang mở cửa tại thời điểm check_time_str (HH:MM) không (Business Rule 2)"""
    ot = p.get("open_time")
    ct = p.get("close_time")
    if not ot or not ct or ot == "Chưa rõ" or ct == "Chưa rõ":
        return True
    try:
        parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', check_time_str)
        if not parts:
            return True
        check_mins = int(parts[0][0]) * 60 + int(parts[0][1] or 0)

        ot_parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', ot)
        ct_parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', ct)
        if not ot_parts or not ct_parts:
            return True
        p_start = int(ot_parts[0][0]) * 60 + int(ot_parts[0][1] or 0)
        p_end = int(ct_parts[0][0]) * 60 + int(ct_parts[0][1] or 0)
        if p_end <= p_start:
            p_end += 24 * 60
            if check_mins < p_start:
                check_mins += 24 * 60
        return p_start <= check_mins <= p_end
    except Exception:
        return True

def is_place_open_during_window(p: dict, free_time_str: str) -> bool:
    """Kiểm tra quán có mở cửa trong khung giờ rảnh không (Business Rule 2)"""
    ot = p.get("open_time")
    ct = p.get("close_time")
    if not ot or not ct or ot == "Chưa rõ" or ct == "Chưa rõ":
        return True
    try:
        parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', free_time_str)
        if len(parts) >= 2:
            req_start = int(parts[0][0]) * 60 + int(parts[0][1] or 0)
            req_end = int(parts[1][0]) * 60 + int(parts[1][1] or 0)
        elif len(parts) == 1:
            req_start = int(parts[0][0]) * 60 + int(parts[0][1] or 0)
            req_end = req_start + 120
        else:
            return True

        if req_end <= req_start:
            req_end += 24 * 60

        ot_parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', ot)
        ct_parts = re.findall(r'(\d{1,2})[:hH](\d{0,2})', ct)
        if not ot_parts or not ct_parts:
            return True
        p_start = int(ot_parts[0][0]) * 60 + int(ot_parts[0][1] or 0)
        p_end = int(ct_parts[0][0]) * 60 + int(ct_parts[0][1] or 0)
        if p_end <= p_start:
            p_end += 24 * 60

        return not (req_end < p_start or req_start > p_end)
    except Exception:
        return True

@app.post("/api/ai-itinerary")
def generate_itinerary(req: ItineraryRequest):
    all_places = get_all_places(include_hidden=False)
    if not all_places:
        raise HTTPException(status_code=500, detail="Cơ sở dữ liệu đang rỗng.")

    # 1. RÀNG BUỘC NGHIỆP VỤ BẮT BUỘC (BUSINESS RULE 3 & KIỂM THỬ BẮT BUỘC)
    free_duration = parse_free_time_minutes(req.free_time)
    target_budget = parse_target_budget_amount(req)

    # Ràng buộc thời gian rảnh: Tối thiểu 60 phút cho lịch trình 3 trạm
    if free_duration < 60:
        return {
            "feasible": False,
            "error_code": "TIME_TOO_SHORT",
            "message": f"Khung giờ rảnh của bạn ({free_duration} phút) quá ngắn để hoàn thành lịch trình 3 trạm (tối thiểu cần 60 - 90 phút).",
            "suggestion": "Bạn hãy mở rộng khung giờ rảnh lên tối thiểu 90 phút (ví dụ: '18:00 - 20:30' hoặc '14:00 - 18:30') để có trải nghiệm trọn vẹn nhất nhé!",
            "recommended_time": "14:00 - 18:30",
            "recommended_budget": target_budget
        }

    # Ràng buộc ngân sách: Nếu đi ăn uống mà ngân sách < 40k (không phải chọn 0đ)
    if req.purpose in ["an_uong", "ca_hai"] and req.budget_level != "free" and target_budget < 40000:
        return {
            "feasible": False,
            "error_code": "BUDGET_TOO_LOW",
            "message": f"Ngân sách ({target_budget:,}đ) quá thấp cho lộ trình ẩm thực 3 trạm tại TP.HCM.",
            "suggestion": "Bạn hãy nới ngân sách lên tối thiểu 80.000đ - 100.000đ hoặc chuyển sang mục đích 'Chỉ đi Tham quan' để check-in các điểm 0đ nhé!",
            "recommended_time": req.free_time,
            "recommended_budget": 100000
        }

    # 1. Xác định toạ độ điểm xuất phát (Ưu tiên GPS chính xác từ Geolocation API của trình duyệt)
    if req.start_lat and req.start_lon:
        start_lat, start_lon = float(req.start_lat), float(req.start_lon)
    else:
        start_lat, start_lon = resolve_start_coords(req.start_location)

    # Tạo bản đồ ID -> place để tra cứu nhanh
    places_by_id = {p["id"]: p for p in all_places}

    # 2. Tạo tóm tắt ngữ cảnh 40 địa điểm thực tế để đưa vào Gemini AI
    places_lines = []
    for p in all_places:
        cat = "Ẩm thực" if p.get("category") == "an_uong" else "Đi chơi/Di tích"
        dishes = p.get("must_try_dishes") or p.get("description") or ""
        places_lines.append(f"ID {p['id']}: {p['name']} | Thể loại: {cat} | Giờ mở: {p.get('open_time')}-{p.get('close_time')} | Đánh giá: {p.get('rating')} sao | Điểm nổi bật: {dishes[:80]}")
    places_context = "\n".join(places_lines)

    selected_ids = []
    overall_advice = ""
    gemini_stops_info = {}
    model_choice = req.ai_model or "gemini-3.8-flash"
    actual_model = model_choice

    companion_map = {
        "di_1_minh": "Đi một mình (Solo)",
        "nguoi_yeu": "Cặp đôi / Người yêu (Hẹn hò lãng mạn)",
        "ban_be": "Nhóm bạn thân",
        "gia_dinh": "Gia đình (Có người lớn / trẻ em)"
    }
    companion_str = companion_map.get(req.companion or "ban_be", "Nhóm bạn thân")

    purpose_map = {
        "an_uong": "Chỉ đi Ăn uống (Thưởng thức ẩm thực đặc sản)",
        "di_choi": "Chỉ đi Vui chơi (Tham quan di tích, check-in, chụp ảnh, cà phê - TUYỆT ĐỐI KHÔNG ăn no)",
        "ca_hai": "Cả hai (Kết hợp vừa ăn đặc sản vừa tham quan/vui chơi/cafe)"
    }
    purpose_str = purpose_map.get(req.purpose or "ca_hai", "Cả hai (Ăn uống và Vui chơi)")

    takenote_str = req.takenote or req.context or "Không có ghi chú loại trừ đặc biệt."

    # 3. Sử dụng Google Gemini AI để thấu hiểu ngữ cảnh và chọn 3 trạm phù hợp nhất (COULD G6-FR11)
    if ai_client and req.ai_model not in ["none", "rule_based", "off"]:
        prompt = f"""Bạn là Chuyên gia Lập Lộ trình Du lịch & Ẩm thực Sài Gòn (TP.HCM) cho nền tảng SGGo! Travel Guide.
YÊU CỦA NGƯỜI DÙNG:
- Điểm xuất phát: "{req.start_location}"
- Khung giờ rảnh: "{req.free_time}"
- Bạn đồng hành: "{companion_str}"
- Mục đích chuyến đi: "{purpose_str}"
- Ghi chú & Yêu cầu riêng (Take note): "{takenote_str}"

KHO DỮ LIỆU ĐỊA ĐIỂM XÁC THỰC CỦA HỆ THỐNG TẠI TP.HCM:
{places_context}

QUY TẮC BẮT BUỘC KHI LẬP LỘ TRÌNH:
1. MỤC ĐÍCH CHUYẾN ĐI:
   - Nếu là "Chỉ đi Vui chơi": 3 trạm PHẢI LÀ điểm tham quan, di tích văn hóa, check-in hoặc quán cà phê/trà/tráng miệng! TUYỆT ĐỐI KHÔNG CHỌN quán cơm, bún, phở, mì, lẩu ăn no!
   - Nếu là "Chỉ đi Ăn uống": 3 trạm tập trung vào các quán đặc sản, ăn vặt, ẩm thực no say và chè đêm.
   - Nếu là "Cả hai": Kết hợp hài hòa 1 điểm tham quan/check-in + 1 quán ăn đặc sản + 1 quán cà phê/trà.
2. BẠN ĐỒNG HÀNH:
   - "Cặp đôi / Người yêu": Ưu tiên quán có không gian lãng mạn, ấm cúng, view đẹp hoặc ánh đèn lung linh.
   - "Nhóm bạn thân": Không gian vui vẻ, rôm rả, đồ ăn dễ chia sẻ.
   - "Gia đình": Không gian thoáng mát, sạch sẽ, dễ đi lại cho người lớn tuổi và trẻ nhỏ.
   - "Đi một mình": Không gian yên tĩnh, phục vụ nhanh, thoải mái.
3. GHI CHÚ ĐẶC BIỆT (TAKE NOTE) - CỰC KỲ QUAN TRỌNG:
   - Nếu người dùng ghi "chán chỗ X", "loại trừ X", "không thích X", "đã đi X nhiều lần" -> TUYỆT ĐỐI KHÔNG CHỌN ĐỊA ĐIỂM ĐÓ!
   - Nếu người dùng ghi "không ăn cay", "thích máy lạnh", "dễ gửi xe" -> Ưu tiên các điểm phù hợp.
4. KIỂM TRA GIỜ MỞ CỬA: Các địa điểm được chọn PHẢI ĐANG MỞ CỬA trong khung giờ rảnh "{req.free_time}".
5. Chọn chính xác 3 địa điểm từ danh sách trên theo thứ tự hợp lý và chia khung giờ cụ thể nằm trọn trong "{req.free_time}".
6. Trả về ĐÚNG định dạng JSON sau (không dùng bất kỳ chữ nào ngoài JSON):
{{
  "selected_ids": [id1, id2, id3],
  "overall_advice": "Đoạn văn 2-3 câu ngắn gọn, súc tích giải thích vì sao chọn lộ trình này phù hợp tuyệt đối với bạn đồng hành, mục đích chuyến đi và ghi chú riêng của người dùng.",
  "stops": [
    {{
      "place_id": id1,
      "time_slot": "hh:mm - hh:mm",
      "action_title": "Tiêu đề chặng ngắn gọn",
      "ai_reason": "Lý do chọn điểm này theo đúng bối cảnh, đồng hành và mục đích của khách",
      "must_try_tip": "Mẹo trải nghiệm hoặc món nên gọi / góc chụp ảnh đẹp"
    }}
  ]
}}
"""
        models_to_try = [model_choice] + [m for m in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-flash-latest"] if m != model_choice]
        for model_name in models_to_try:
            try:
                res = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if res and res.text:
                    raw_text = res.text.strip()
                    clean_json = raw_text
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_json:
                        clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    
                    parsed = json.loads(clean_json)
                    s_ids = parsed.get("selected_ids", [])
                    if len(s_ids) >= 3 and all(pid in places_by_id for pid in s_ids[:3]) and len(set(s_ids[:3])) == 3:
                        selected_ids = s_ids[:3]
                        overall_advice = parsed.get("overall_advice", "")
                        for st in parsed.get("stops", []):
                            gemini_stops_info[st.get("place_id")] = st
                        actual_model = model_name
                        break
            except Exception:
                continue

    # 4. Fallback phòng hộ nếu Gemini AI không kết nối được hoặc dùng Rule-Based Heuristic
    if len(selected_ids) < 3:
        # Lọc theo giờ mở cửa (Business Rule 2: địa điểm đóng cửa/ẩn không đưa vào lịch trình)
        open_cands = [p for p in all_places if is_place_open_during_window(p, req.free_time)]
        valid_pool = open_cands if len(open_cands) >= 10 else all_places

        if req.purpose == "di_choi":
            candidates = [p for p in valid_pool if p.get("category") == "di_choi"]
            if len(candidates) < 3:
                candidates += [p for p in valid_pool if "cafe" in remove_accent(p.get("name", "")).lower() or "che" in remove_accent(p.get("name", "")).lower()]
        elif req.purpose == "an_uong":
            candidates = [p for p in valid_pool if p.get("category") == "an_uong"]
        else:
            candidates = valid_pool

        # Lọc theo ngân sách nếu chọn Miễn phí (0đ)
        if req.budget_level == "free" or target_budget == 0:
            free_cands = [p for p in candidates if (p.get("min_price") or 0) == 0 and (p.get("max_price") or 0) == 0]
            if len(free_cands) >= 3:
                candidates = free_cands

        # Xáo trộn danh sách ứng viên theo shuffle_seed (G6-FR06: Xáo trộn/Đổi phương án khác)
        if req.shuffle_seed and req.shuffle_seed > 0:
            shift = (req.shuffle_seed * 4) % max(1, len(candidates))
            candidates = candidates[shift:] + candidates[:shift]

        # Lọc loại trừ theo Take note (Hỗ trợ cả tên viết tắt, tên phụ, từ khóa như 'chùa bà', 'cả cần', 'hà ký')
        if req.takenote:
            tn_clean = remove_accent(req.takenote).lower()
            filtered_cands = []
            for p in candidates:
                raw_name = p.get("name", "")
                base_name = raw_name.split("(")[0].strip()
                norm_full = remove_accent(raw_name).lower()
                norm_base = remove_accent(base_name).lower()

                is_excluded = False
                if norm_base and norm_base in tn_clean:
                    is_excluded = True
                elif norm_full and norm_full in tn_clean:
                    is_excluded = True
                else:
                    # Kiểm tra các cụm 2 từ đặc trưng (VD: 'chua ba', 'thien hau', 'ca can', 'ha ky')
                    words = [w for w in norm_base.split() if len(w) > 1]
                    for i in range(len(words) - 1):
                        bigram = f"{words[i]} {words[i+1]}"
                        if bigram in tn_clean and bigram not in ["quan 5", "tp hcm", "sai gon", "duong an", "hoi quan", "thanh pho"]:
                            is_excluded = True
                            break

                if not is_excluded:
                    filtered_cands.append(p)

            if len(filtered_cands) >= 3:
                candidates = filtered_cands

        # Sắp xếp ứng viên theo cự ly gần nhất từ điểm xuất phát và áp dụng Sliding Window theo shuffle_seed
        seed = req.shuffle_seed or 0

        # Đối với mục đích 'Cả hai': Đảm bảo kết hợp hài hòa cả Ẩm thực lẫn Vui chơi/Di tích/Cafe
        if req.purpose == "ca_hai":
            play_cands = [p for p in candidates if p.get("category") == "di_choi"]
            eat_cands = [p for p in candidates if p.get("category") == "an_uong"]
            if play_cands and eat_cands:
                play_sorted = sorted(play_cands, key=lambda p: calculate_haversine_distance(start_lat, start_lon, p.get("lat") or 10.75, p.get("lon") or 106.66))
                eat_sorted = sorted(eat_cands, key=lambda p: calculate_haversine_distance(start_lat, start_lon, p.get("lat") or 10.75, p.get("lon") or 106.66))
                
                off_play = (seed * 2) % max(1, len(play_sorted) - 2) if len(play_sorted) > 3 else 0
                off_eat = (seed * 3) % max(1, len(eat_sorted) - 3) if len(eat_sorted) > 4 else 0
                
                win_play = play_sorted[off_play:off_play + 6]
                win_eat = eat_sorted[off_eat:off_eat + 8]
                
                opt_play = optimize_route_nearest_neighbor((start_lat, start_lon), win_play, max_stops=1)
                opt_eat = optimize_route_nearest_neighbor((start_lat, start_lon), win_eat, max_stops=2)
                combo = opt_play + opt_eat
                opt_stops = optimize_route_nearest_neighbor((start_lat, start_lon), combo, max_stops=3)
            else:
                c_sorted = sorted(candidates, key=lambda p: calculate_haversine_distance(start_lat, start_lon, p.get("lat") or 10.75, p.get("lon") or 106.66))
                off = (seed * 3) % max(1, len(c_sorted) - 4) if len(c_sorted) > 5 else 0
                opt_stops = optimize_route_nearest_neighbor((start_lat, start_lon), c_sorted[off:off + 10], max_stops=3)
        else:
            c_sorted = sorted(candidates, key=lambda p: calculate_haversine_distance(start_lat, start_lon, p.get("lat") or 10.75, p.get("lon") or 106.66))
            off = (seed * 3) % max(1, len(c_sorted) - 4) if len(c_sorted) > 5 else 0
            opt_stops = optimize_route_nearest_neighbor((start_lat, start_lon), c_sorted[off:off + 10], max_stops=3)

        selected_ids = [p["id"] for p in opt_stops]
        overall_advice = f"Lộ trình 3 trạm tối ưu xuất phát từ '{req.start_location}', sắp xếp theo khung giờ {req.free_time} cho {companion_str} với mục đích {purpose_str}."

    chosen_places = [places_by_id[pid] for pid in selected_ids if pid in places_by_id]
    if len(chosen_places) < 3:
        chosen_places = all_places[:3]

    # 5. Sắp xếp thứ tự các trạm:
    # Nếu Gemini AI đã lập lịch trình với mốc giờ cụ thể, tôn trọng thứ tự thời gian của Gemini.
    # Nếu dùng thuật toán dự phòng, sắp xếp theo khoảng cách láng giềng gần nhất.
    if gemini_stops_info:
        optimized_places = [places_by_id[pid] for pid in selected_ids if pid in places_by_id]
    else:
        optimized_places = optimize_route_nearest_neighbor((start_lat, start_lon), chosen_places, max_stops=3)
    if not optimized_places:
        optimized_places = chosen_places

    # 6. Tạo đường link Google Maps Multi-stop dẫn đường xe máy liên hoàn 3 trạm
    p1, p2, p3 = optimized_places[0], optimized_places[1], optimized_places[2]
    lat0, lon0 = start_lat, start_lon
    gmaps_multi_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={lat0},{lon0}"
        f"&destination={p3['lat']},{p3['lon']}"
        f"&waypoints={p1['lat']},{p1['lon']}|{p2['lat']},{p2['lon']}"
        f"&travelmode=two_wheeler"
    )

    # 7. Xây dựng dữ liệu Timeline chi tiết & Tính toán KPI ràng buộc (G6-FR05 & Section 5)
    steps = []
    stops_db_data = []
    curr_lat, curr_lon = start_lat, start_lon
    total_dist = 0.0
    total_t_min = 0

    for idx, spot in enumerate(optimized_places):
        p_lat = spot.get("lat") or 10.7550
        p_lon = spot.get("lon") or 106.6650
        dist = round(calculate_haversine_distance(curr_lat, curr_lon, p_lat, p_lon), 2)
        t_min = max(3, int(round(dist * 3.5)))
        total_dist += dist
        total_t_min += t_min
        curr_lat, curr_lon = p_lat, p_lon

        ai_info = gemini_stops_info.get(spot["id"], {})
        slot_time = ai_info.get("time_slot") or f"Chặng {idx+1} ({t_min + 45} phút)"
        action_title = ai_info.get("action_title") or f"Trạm {idx+1}: Khám phá {spot['name']} [{ 'Ẩm thực' if spot.get('category') == 'an_uong' else 'Đi chơi/Di tích' }]"
        ai_reason = ai_info.get("ai_reason", "Địa điểm mở cửa phù hợp, láng giềng gần nhất tối ưu lộ trình di chuyển.")
        must_try_tip = ai_info.get("must_try_tip", spot.get("must_try_dishes") or "Trải nghiệm không gian đặc sắc.")

        if dist < 0.8:
            traffic_note = "Rất gần trạm trước, di chuyển thuận chiều, không lo quay đầu xe."
        elif dist < 2.5:
            traffic_note = "Đoạn đường ngắn nội quận, chú ý đèn tín hiệu tại các ngã tư."
        else:
            traffic_note = f"Khoảng cách ~{dist} km, nên đi sớm tránh giờ tan tầm kẹt xe."

        p_min_cost = spot.get("min_price", 0)
        p_max_cost = spot.get("max_price", 0)

        # Xây dựng giải thích rule minh bạch (G6-FR10 SHOULD)
        mapped_comp_tag = {"ban_be": "nhom_ban", "nguoi_yeu": "hen_ho", "gia_dinh": "gia_dinh", "di_1_minh": "di_1_minh"}.get(req.companion, "nhom_ban")
        tier_pts, fit_tier = get_companion_tier_score(spot, mapped_comp_tag)
        rule_reasons = []
        if tier_pts > 0:
            rule_reasons.append(f"Khớp bối cảnh '{companion_str}' (+{int(tier_pts)}đ {fit_tier})")
        rule_reasons.append(f"Mở cửa ({spot.get('open_time')}-{spot.get('close_time')})")
        avg_cost = (p_min_cost + p_max_cost) // 2
        rule_reasons.append(f"Chi phí ~{avg_cost:,}đ")
        rule_reasons.append(f"Cách trạm trước {dist} km")
        rule_explanation = " • ".join(rule_reasons)

        step_dict = {
            "place_id": spot.get("id"),
            "time": slot_time,
            "action": action_title,
            "location": f"{spot['name']} — {spot.get('address')} ⭐ {spot.get('rating')}".strip(),
            "travel_info": f"Di chuyển ~{dist} km (~{t_min} phút xe máy)",
            "traffic_warning": traffic_note,
            "ai_reason": ai_reason,
            "rule_explanation": rule_explanation,
            "must_try_tip": must_try_tip,
            "image_url": spot.get("image_url"),
            "open_hours": f"{spot.get('open_time')} - {spot.get('close_time')}",
            "price_range": f"{p_min_cost:,}đ - {p_max_cost:,}đ",
            "lat": p_lat,
            "lon": p_lon,
            "dist": dist,
            "t_min": t_min
        }
        steps.append(step_dict)

        stops_db_data.append({
            "place_id": spot.get("id"),
            "stop_order": idx + 1,
            "time_slot": slot_time,
            "action_title": action_title,
            "travel_distance_km": dist,
            "travel_time_minutes": t_min,
            "estimated_cost_min": p_min_cost,
            "estimated_cost_max": p_max_cost
        })

    # Tính tổng ngân sách & tổng thời gian (G6-FR05 MUST)
    total_min_cost = sum(spot.get("min_price", 0) for spot in optimized_places)
    total_max_cost = sum(spot.get("max_price", 0) for spot in optimized_places)
    total_stay_mins = len(optimized_places) * 45  # Giả định 45 phút mỗi trạm
    total_duration_minutes = total_t_min + total_stay_mins

    is_within_budget = (target_budget == 0 and total_min_cost == 0) or (total_min_cost <= target_budget * 1.25)
    is_within_time = total_duration_minutes <= (free_duration + 30)

    # Lưu lịch trình vào CSDL SQLite (Section 5 ERD & Data Dictionary)
    itin_id = None
    try:
        itin_id = save_itinerary({
            "user_id": None,
            "start_location": req.start_location,
            "start_lat": start_lat,
            "start_lon": start_lon,
            "free_time": req.free_time,
            "companion": req.companion,
            "purpose": req.purpose,
            "budget_level": req.budget_level or req.budget,
            "target_budget": target_budget,
            "total_estimated_budget_min": total_min_cost,
            "total_estimated_budget_max": total_max_cost,
            "total_duration_minutes": total_duration_minutes,
            "summary": overall_advice
        }, stops_db_data)
    except Exception as e:
        print(f"Lưu itinerary DB log: {e}")

    return {
        "feasible": True,
        "itinerary_id": itin_id,
        "summary": overall_advice,
        "steps": steps,
        "model_used": actual_model,
        "start_coords": {"lat": start_lat, "lon": start_lon},
        "gmaps_multi_url": gmaps_multi_url,
        "kpi": {
            "target_budget": target_budget,
            "total_min_cost": total_min_cost,
            "total_max_cost": total_max_cost,
            "is_within_budget": is_within_budget,
            "free_duration_minutes": free_duration,
            "total_duration_minutes": total_duration_minutes,
            "total_travel_distance_km": round(total_dist, 2),
            "total_travel_time_minutes": total_t_min,
            "is_within_time": is_within_time
        }
    }



# ==============================================================================
# CÁC API QUẢN TRỊ DÀNH CHO ADMIN (ADMIN CRUD & IMPORT CSV)
# ==============================================================================

@app.post("/api/admin/places")
def create_new_place(place: PlaceModel):
    new_p = add_place(place.model_dump())
    return {"status": "ok", "place": new_p}

@app.put("/api/admin/places/{place_id}")
def modify_place(place_id: int, place: PlaceModel):
    updated = update_place(place_id, place.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm để cập nhật.")
    return {"status": "ok", "place": updated}

@app.delete("/api/admin/places/{place_id}")
def remove_place(place_id: int):
    delete_place(place_id)
    return {"status": "ok", "message": "Đã xóa địa điểm thành công."}

@app.post("/api/admin/places/{place_id}/toggle-hide")
def toggle_admin_place_hide(place_id: int):
    res = toggle_hide_place(place_id)
    if not res:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm.")
    return {"status": "ok", "place": res}

@app.get("/api/admin/sample-csv")
def download_sample_csv():
    csv_text = generate_sample_csv()
    return Response(content=csv_text, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=template_places.csv"
    })

@app.post("/api/admin/extract-gmaps")
def extract_gmaps_info(req: ExtractGmapsRequest):
    raw_input = req.url_or_query.strip()
    if not raw_input:
        raise HTTPException(status_code=400, detail="Vui lòng nhập link Google Maps hoặc tên quán.")

    extracted_name = ""
    extracted_address = "Quận 5, TP.HCM"
    extracted_lat = 10.7550
    extracted_lon = 106.6650
    extracted_image = ""

    target_url = raw_input
    if target_url.startswith("google.com") or target_url.startswith("www.google.com") or target_url.startswith("maps.google.com"):
        target_url = "https://" + target_url

    is_url = target_url.startswith("http://") or target_url.startswith("https://") or "maps." in target_url or "goo.gl" in target_url or "google.com" in target_url

    if is_url:
        import requests
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "vi,en;q=0.9"
            }
            resp = requests.get(target_url, allow_redirects=True, timeout=8, headers=headers)
            final_url = resp.url
            html = resp.text

            # Kiểm tra redirect qua thẻ meta refresh nếu có
            if "maps.app.goo.gl" in final_url or "goo.gl/maps" in final_url:
                meta_ref = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][0-9]+;\s*url=([^"\']+)["\']', html, re.IGNORECASE)
                if meta_ref:
                    final_url = meta_ref.group(1).replace("&amp;", "&")

            # 1. Trích xuất tên quán từ final_url
            m_place = re.search(r'/place/([^/@?]+)', final_url)
            if m_place:
                extracted_name = urllib.parse.unquote_plus(m_place.group(1)).replace("+", " ").strip()
            elif "/search/" in final_url:
                m_search = re.search(r'/search/([^/@?]+)', final_url)
                if m_search:
                    extracted_name = urllib.parse.unquote_plus(m_search.group(1)).replace("+", " ").strip()
            elif "?q=" in final_url or "&q=" in final_url or "?query=" in final_url:
                m_q = re.search(r'[?&](?:q|query)=([^&]+)', final_url)
                if m_q:
                    extracted_name = urllib.parse.unquote_plus(m_q.group(1)).replace("+", " ").strip()

            # 2. Trích xuất tọa độ GPS
            m_coords = re.search(r'/@([0-9.]+),([0-9.]+)', final_url)
            if m_coords:
                extracted_lat = float(m_coords.group(1))
                extracted_lon = float(m_coords.group(2))
            else:
                m_data_coords = re.search(r'!3d([0-9.]+)!4d([0-9.]+)', final_url)
                if m_data_coords:
                    extracted_lat = float(m_data_coords.group(1))
                    extracted_lon = float(m_data_coords.group(2))

            # 3. Trích xuất og:title, og:description, og:image
            og_title = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
            if og_title:
                t_val = og_title.group(1).replace("· Google Maps", "").replace("- Google Maps", "").strip()
                if t_val and "Google Maps" not in t_val:
                    if not extracted_name or len(t_val) > len(extracted_name):
                        extracted_name = t_val

            og_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html)
            if og_desc:
                desc_text = og_desc.group(1).strip()
                if any(w in desc_text for w in ["Quận", "Phường", "Đường", "TP", "Hồ Chí Minh"]):
                    parts = desc_text.split("·")
                    if len(parts) > 1:
                        extracted_address = parts[-1].strip()
                    else:
                        extracted_address = desc_text

            og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
            if og_img and ("googleusercontent" in og_img.group(1) or "streetview" in og_img.group(1)):
                extracted_image = og_img.group(1)

        except Exception:
            pass
    else:
        extracted_name = raw_input

    # Nếu tên quán có chứa luôn địa chỉ dạng "Tên Quán, Số nhà, Phường, Quận 5..."
    if "," in extracted_name and any(k in extracted_name for k in ["Quận", "Phường", "Đường"]):
        parts = extracted_name.split(",", 1)
        extracted_name = parts[0].strip()
        extracted_address = parts[1].strip()

    if not extracted_name or extracted_name.startswith("http"):
        extracted_name = raw_input.rstrip("/").split("/")[-1].replace("+", " ").replace("-", " ")

    extracted_name = ' '.join(w.capitalize() for w in extracted_name.split())

    # Quy chuẩn thông tin mặc định thông minh
    name_clean = remove_accent(extracted_name)
    is_food = any(k in name_clean for k in [
        "quan", "tiem", "com", "pho", "hu tieu", "sui cao", "dimsum", "lau", "banh",
        "che", "tra sua", "cafe", "coffee", "tea", "nuoc", "food", "an", "bun", "oc", "ga", "bo"
    ])
    
    category = "an_uong" if is_food else "di_choi"
    open_time = "06:30" if any(k in name_clean for k in ["cafe", "coffee", "pho", "hu tieu", "bun"]) else ("10:30" if category == "an_uong" else "07:30")
    close_time = "22:30" if category == "an_uong" else "18:00"
    min_price = 45000 if category == "an_uong" else 0
    max_price = 95000 if category == "an_uong" else 30000
    rating = 4.5
    reviews_count = 150
    peak_hours = "18:30 - 20:30" if category == "an_uong" else "09:00 - 11:00"
    best_review = ""
    worst_review = ""
    tags = "nhom_ban,di_1_minh,hen_ho"

    # Kiểm tra trước trong CSDL xem có khớp với quán nào sẵn có không (Tối ưu phản hồi < 5ms)
    conn = get_connection()
    cursor = conn.cursor()
    search_term = extracted_name if extracted_name and not extracted_name.startswith("http") else raw_input
    cursor.execute("SELECT * FROM places WHERE name LIKE ? OR ? LIKE ('%' || name || '%')", 
                   (f"%{search_term}%", raw_input))
    found = cursor.fetchone()
    conn.close()
    if found:
        matched = dict(found)
        return {
            "status": "ok",
            "place": {
                "name": matched["name"],
                "category": matched["category"],
                "address": matched["address"],
                "district": matched["district"],
                "lat": matched["lat"],
                "lon": matched["lon"],
                "open_time": matched["open_time"],
                "close_time": matched["close_time"],
                "min_price": matched["min_price"],
                "max_price": matched["max_price"],
                "rating": matched["rating"],
                "reviews_count": matched["reviews_count"],
                "peak_hours": matched["peak_hours"],
                "best_review": matched["best_review"],
                "worst_review": matched["worst_review"],
                "image_url": matched["image_url"],
                "tags": matched["tags"],
                "is_verified": 1
            }
        }

    # Gọi Gemini 3.8 Flash AI nếu là quán mới
    if ai_client:
        try:
            prompt = (
                f"Địa điểm: '{extracted_name}' tại Quận 5, TP.HCM (tọa độ tham khảo: {extracted_lat}, {extracted_lon}). "
                f"Hãy phân tích và trả về đúng 1 JSON duy nhất có các trường: "
                f"name (tên quán chuẩn tiếng Việt có dấu), "
                f"category ('an_uong' hoặc 'di_choi'), "
                f"address (địa chỉ thật cụ thể có số nhà, đường, phường, Quận 5), "
                f"district ('Quận 5'), "
                f"lat (float vĩ độ thực tế tại Quận 5), "
                f"lon (float kinh độ thực tế tại Quận 5), "
                f"open_time (định dạng HH:MM, VD '07:00'), "
                f"close_time (định dạng HH:MM, VD '22:30'), "
                f"min_price (số nguyên VNĐ), "
                f"max_price (số nguyên VNĐ), "
                f"rating (float từ 4.0 đến 4.8), "
                f"reviews_count (số nguyên lượng đánh giá), "
                f"peak_hours (chuỗi giờ cao điểm thật), "
                f"best_review (Trích dẫn 1 câu nhận xét 5 sao thực tế của khách hàng trên Google Maps, kèm tên người đánh giá nếu có), "
                f"worst_review (Trích dẫn 1 câu nhận xét 1-3 sao hoặc góp ý thực tế của khách về giờ chờ/bãi xe/hương vị trên Google Maps, kèm tên người đánh giá nếu có), "
                f"tags (chuỗi phân cách dấu phẩy: di_1_minh, hen_ho, nhom_ban, gia_dinh)."
                f"Chỉ trả về duy nhất khối JSON."
            )
            res = ai_client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
            if res.text:
                json_match = re.search(r'\{.*\}', res.text, re.DOTALL)
                if json_match:
                    ai_data = json.loads(json_match.group(0))
                    if ai_data.get("name"):
                        extracted_name = ai_data["name"]
                    category = ai_data.get("category", category)
                    if ai_data.get("address"):
                        extracted_address = ai_data["address"]
                    if ai_data.get("lat"):
                        extracted_lat = float(ai_data["lat"])
                    if ai_data.get("lon"):
                        extracted_lon = float(ai_data["lon"])
                    open_time = ai_data.get("open_time", open_time)
                    close_time = ai_data.get("close_time", close_time)
                    min_price = int(ai_data.get("min_price", min_price))
                    max_price = int(ai_data.get("max_price", max_price))
                    rating = float(ai_data.get("rating", rating))
                    reviews_count = int(ai_data.get("reviews_count", reviews_count))
                    peak_hours = ai_data.get("peak_hours", peak_hours)
                    best_review = ai_data.get("best_review", best_review)
                    worst_review = ai_data.get("worst_review", worst_review)
                    tags = ai_data.get("tags", tags)
        except Exception:
            pass

    return {
        "status": "ok",
        "place": {
            "name": extracted_name,
            "category": category,
            "address": extracted_address,
            "district": "Quận 5",
            "lat": extracted_lat,
            "lon": extracted_lon,
            "open_time": open_time,
            "close_time": close_time,
            "min_price": min_price,
            "max_price": max_price,
            "rating": rating,
            "reviews_count": reviews_count,
            "peak_hours": peak_hours,
            "best_review": best_review,
            "worst_review": worst_review,
            "image_url": extracted_image if (extracted_image and str(extracted_image).strip()) else None,
            "tags": tags,
            "is_verified": 1
        }
    }



class TagCreateRequest(BaseModel):
    tag_key: str
    name: str
    tier_type: Optional[str] = "companion"

class TagUpdateRequest(BaseModel):
    name: str
    is_active: Optional[int] = 1

class ImportCSVRequest(BaseModel):
    csv_content: str
    filename: Optional[str] = "places_import.csv"

@app.post("/api/admin/import-csv")
def import_csv_places(req: ImportCSVRequest):
    res = import_csv_data(req.csv_content, filename=req.filename or "places_import.csv")
    return {
        "status": "ok",
        "imported_count": res.get("success_count", 0),
        "error_count": res.get("error_count", 0),
        "total_rows": res.get("total_rows", 0),
        "errors": res.get("errors", [])
    }

@app.get("/api/admin/import-logs")
def admin_get_import_logs(limit: int = 10):
    return get_import_logs(limit=limit)

@app.get("/api/admin/stats")
def get_admin_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM places")
    total_places = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM places WHERE is_verified = 1")
    verified_places = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()
    return {
        "total_places": total_places,
        "verified_places": verified_places,
        "total_users": total_users,
        "total_favorites": 0
    }

@app.get("/api/admin/users")
def admin_get_users():
    return get_all_users()

@app.put("/api/admin/users/{user_id}/role")
def admin_update_user_role(user_id: int, req: UserRoleUpdate):
    ok, msg = update_user_role(user_id, req.role)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok", "message": msg}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int):
    ok, msg = delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok", "message": msg}


# ==========================================
# API QUẢN LÝ TAG & BỘ LỌC (G6-FR08 & Section 5 ERD)
# ==========================================
@app.get("/api/admin/tags")
def admin_get_tags():
    """API lấy danh sách toàn bộ tag cùng số lượng quán sử dụng (G6-FR08)"""
    return {"status": "success", "tags": get_all_tags()}

@app.post("/api/admin/tags")
def admin_add_tag(req: TagCreateRequest):
    """API thêm tag mới vào hệ thống (G6-FR08)"""
    res = add_tag(req.tag_key, req.name, req.tier_type)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.put("/api/admin/tags/{tag_id}")
def admin_update_tag(tag_id: int, req: TagUpdateRequest):
    """API cập nhật thông tin tag (G6-FR08)"""
    success = update_tag(tag_id, req.name, req.is_active)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tag")
    return {"status": "success", "tag_id": tag_id}

@app.delete("/api/admin/tags/{tag_id}")
def admin_delete_tag(tag_id: int):
    """API xóa tag khỏi hệ thống (G6-FR08)"""
    success = delete_tag(tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tag")
    return {"status": "success", "tag_id": tag_id}

@app.post("/api/admin/tags/{tag_id}/toggle")
def admin_toggle_tag(tag_id: int, payload: dict = Body(...)):
    """API bật/tắt trạng thái tag (G6-FR08)"""
    is_active = int(payload.get("is_active", 1))
    success = toggle_tag_active(tag_id, is_active)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tag")
    return {"status": "success", "tag_id": tag_id, "is_active": is_active}

# ==============================================================================
# PHỤC VỤ GIAO DIỆN FRONTEND TĨNH (STATIC MOUNT)
# ==============================================================================

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
