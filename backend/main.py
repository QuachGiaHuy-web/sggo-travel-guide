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
    toggle_favorite, get_user_favorites, generate_sample_csv, import_csv_data,
    get_connection, get_all_users, update_user_role, delete_user
)

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

class UserRoleUpdate(BaseModel):
    role: str

class ExtractGmapsRequest(BaseModel):
    url_or_query: str

class ItineraryRequest(BaseModel):
    start_location: str
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    free_time: str                       # Giờ rảnh cụ thể: '14:00 - 18:30', '19:00 - 22:30', etc.
    companion: Optional[str] = "ban_be"  # 'di_1_minh', 'nguoi_yeu', 'ban_be', 'gia_dinh'
    purpose: Optional[str] = "ca_hai"    # 'an_uong', 'di_choi', 'ca_hai'
    takenote: Optional[str] = ""         # Ghi chú / Take note riêng (VD: chán chỗ X rồi, loại ra...)
    context: Optional[str] = ""          # Giữ tương thích ngược
    budget: Optional[str] = "Vừa vặn thoải mái"
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
               only_verified: Optional[bool] = True):
    return get_all_places(category=category, context_tag=tag, min_budget=min_price, 
                          max_budget=max_price, min_rating=min_rating, search=search, 
                          only_verified=only_verified)

@app.get("/api/places/{place_id}")
def get_place(place_id: int):
    place = get_place_by_id(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm này.")
    return place

# ==============================================================================
# API GỢI Ý NHANH (QUICK RECOMMENDATION - 5 MỨC NGÂN SÁCH & TỰ NHẬP)
# ==============================================================================

@app.post("/api/quick-recommend")
def quick_recommend(req: QuickRecommendRequest):
    """
    Thuật toán phân tích ma trận đa chiều & Chấm điểm độ phù hợp (Smart Scoring):
    1. Lọc thể loại (category): Ẩm thực hoặc Vui chơi
    2. Điểm tương thích đồng hành (context): đi 1 mình, cặp đôi, nhóm bạn, gia đình
    3. Điểm khớp ngân sách (budget): <50k, 50k-100k, 100k-250k, >250k hoặc số tiền tự nhập
    4. Trọng số uy tín (rating, reviews)
    5. Hỗ trợ offset xoay vòng (Đổi gợi ý khác) không bao giờ bị trùng lặp cứng nhắc
    """
    all_places = get_all_places(category=req.category)
    if not all_places:
        all_places = get_all_places()

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

        # 1. Khớp Category
        if req.category and req.category != "all" and p.get("category") != req.category:
            continue

        # 2. Khớp Context (Đồng hành)
        tags = [t.strip() for t in (p.get("tags") or "").split(",") if t.strip()]
        if mapped_tag:
            if mapped_tag in tags:
                idx = tags.index(mapped_tag)
                score += (20.0 - idx * 2.5)
            else:
                score -= 10.0

        # 3. Khớp Ngân sách
        min_p = p.get("min_price", 0)
        max_p = p.get("max_price", 0)
        avg_p = (min_p + max_p) / 2.0

        if p.get("category") == "di_choi" and min_p == 0 and max_p == 0:
            if req.price_level == "under_50k":
                score += 18.0
            elif req.price_level == "50k_100k":
                score += 10.0
            else:
                score += 4.0
        else:
            if req.price_level == "under_50k":
                if max_p <= 60000:
                    score += 20.0
                elif min_p <= 50000:
                    score += 5.0
                else:
                    score -= 30.0
            elif req.price_level == "50k_100k":
                if 40000 <= avg_p <= 115000 or (min_p <= 90000 and max_p >= 50000):
                    score += 20.0
                elif max_p < 40000:
                    score -= 8.0
                else:
                    score -= 22.0
            elif req.price_level == "100k_250k":
                if 90000 <= avg_p <= 260000 or (max_p >= 100000 and min_p <= 250000):
                    score += 20.0
                elif max_p < 90000:
                    score -= 18.0
                else:
                    score += 4.0
            elif req.price_level == "above_250k":
                if max_p >= 200000:
                    score += 25.0
                elif max_p >= 100000:
                    score += 6.0
                else:
                    score -= 25.0
            elif req.price_level == "custom" and req.custom_budget and req.custom_budget > 0:
                cb = req.custom_budget
                if min_p <= cb:
                    ratio = min(avg_p, cb) / max(avg_p, cb, 1)
                    score += 20.0 * ratio
                else:
                    score -= 30.0

        # 4. Trọng số Đánh giá (Rating & Reviews)
        rating = float(p.get("rating", 4.0))
        score += (rating - 4.0) * 6.0

        scored_places.append((score, p))

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
# API LẬP LỘ TRÌNH THÔNG MINH (AI SMART ITINERARY)
# ==============================================================================

@app.post("/api/ai-itinerary")
def generate_itinerary(req: ItineraryRequest):
    all_places = get_all_places()
    if not all_places:
        raise HTTPException(status_code=500, detail="Cơ sở dữ liệu đang rỗng.")

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

    # 3. Sử dụng Google Gemini AI để thấu hiểu ngữ cảnh và chọn 3 trạm phù hợp nhất
    if ai_client:
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

    # 4. Fallback phòng hộ nếu Gemini AI không kết nối được
    if len(selected_ids) < 3:
        if req.purpose == "di_choi":
            candidates = [p for p in all_places if p.get("category") == "di_choi"]
            if len(candidates) < 3:
                candidates += [p for p in all_places if "cafe" in remove_accent(p.get("name", "")).lower() or "che" in remove_accent(p.get("name", "")).lower()]
        elif req.purpose == "an_uong":
            candidates = [p for p in all_places if p.get("category") == "an_uong"]
        else:
            candidates = all_places

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

        # Đối với mục đích 'Cả hai': Đảm bảo kết hợp hài hòa cả Ẩm thực lẫn Vui chơi/Di tích/Cafe
        if req.purpose == "ca_hai":
            play_cands = [p for p in candidates if p.get("category") == "di_choi"]
            eat_cands = [p for p in candidates if p.get("category") == "an_uong"]
            if play_cands and eat_cands:
                opt_play = optimize_route_nearest_neighbor((start_lat, start_lon), play_cands, max_stops=1)
                opt_eat = optimize_route_nearest_neighbor((start_lat, start_lon), eat_cands, max_stops=2)
                combo = opt_play + opt_eat
                opt_stops = optimize_route_nearest_neighbor((start_lat, start_lon), combo, max_stops=3)
            else:
                opt_stops = optimize_route_nearest_neighbor((start_lat, start_lon), candidates, max_stops=3)
        else:
            opt_stops = optimize_route_nearest_neighbor((start_lat, start_lon), candidates, max_stops=3)

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

    # 7. Xây dựng dữ liệu Timeline chi tiết
    steps = []
    curr_lat, curr_lon = start_lat, start_lon
    for idx, spot in enumerate(optimized_places):
        p_lat = spot.get("lat") or 10.7550
        p_lon = spot.get("lon") or 106.6650
        dist = round(calculate_haversine_distance(curr_lat, curr_lon, p_lat, p_lon), 2)
        t_min = max(3, int(round(dist * 3.5)))
        curr_lat, curr_lon = p_lat, p_lon

        ai_info = gemini_stops_info.get(spot["id"], {})
        slot_time = ai_info.get("time_slot") or f"Chặng {idx+1} ({t_min + 45} phút trải nghiệm)"
        action_title = ai_info.get("action_title") or f"Trạm {idx+1}: Khám phá {spot['name']} [{ 'Ẩm thực' if spot.get('category') == 'an_uong' else 'Đi chơi/Di tích' }]"
        ai_reason = ai_info.get("ai_reason", "Địa điểm phù hợp với bối cảnh và thời gian rảnh của bạn.")
        must_try_tip = ai_info.get("must_try_tip", spot.get("must_try_dishes") or "Trải nghiệm không gian đặc sắc.")

        if dist < 0.8:
            traffic_note = "Rất gần trạm trước, di chuyển thuận chiều, không lo quay đầu xe."
        elif dist < 2.5:
            traffic_note = "Đoạn đường ngắn nội quận, chú ý đèn tín hiệu tại các ngã tư."
        else:
            traffic_note = f"Khoảng cách ~{dist} km, nên đi sớm tránh giờ tan tầm kẹt xe."

        steps.append({
            "place_id": spot.get("id"),
            "time": slot_time,
            "action": action_title,
            "location": f"{spot['name']} — {spot.get('address')} ⭐ {spot.get('rating')}".strip(),
            "travel_info": f"Di chuyển ~{dist} km (~{t_min} phút xe máy)",
            "traffic_warning": traffic_note,
            "ai_reason": ai_reason,
            "must_try_tip": must_try_tip,
            "image_url": spot.get("image_url"),
            "open_hours": f"{spot.get('open_time')} - {spot.get('close_time')}",
            "price_range": f"{spot.get('min_price', 0):,}đ - {spot.get('max_price', 0):,}đ",
            "lat": p_lat,
            "lon": p_lon
        })

    return {
        "summary": overall_advice,
        "steps": steps,
        "model_used": actual_model,
        "start_coords": {"lat": start_lat, "lon": start_lon},
        "gmaps_multi_url": gmaps_multi_url
    }

# ==============================================================================
# CÁC API YÊU THÍCH (FAVORITES)
# ==============================================================================

@app.post("/api/favorites/{place_id}")
def toggle_user_favorite(place_id: int, user_id: int = Body(..., embed=True)):
    action = toggle_favorite(user_id, place_id)
    return {"status": "ok", "action": action}

@app.get("/api/favorites")
def get_favorites(user_id: int):
    return get_user_favorites(user_id)

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



@app.post("/api/admin/import-csv")
def import_csv_places(csv_content: str = Body(..., embed=True)):
    count = import_csv_data(csv_content)
    return {"status": "ok", "imported_count": count}

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
    cursor.execute("SELECT COUNT(*) FROM favorites")
    total_favorites = cursor.fetchone()[0]
    conn.close()
    return {
        "total_places": total_places,
        "verified_places": verified_places,
        "total_users": total_users,
        "total_favorites": total_favorites
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

# ==============================================================================
# PHỤC VỤ GIAO DIỆN FRONTEND TĨNH (STATIC MOUNT)
# ==============================================================================

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")