# -*- coding: utf-8 -*-
"""
main.py - BACKEND REST API CHO DỰ ÁN SGGO!
Môn học: Công nghệ Phần mềm (COMP1044)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from backend.database import init_db, get_all_places, get_place_by_id

# Khởi tạo CSDL SQLite khi server bật
init_db()

app = FastAPI(
    title="SGGo! Travel Guide API",
    description="API backend phục vụ cẩm nang du lịch và gợi ý lộ trình thông minh Sài Gòn",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "Chào mừng đến với SGGo! Travel Guide API",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "sggo-backend"}

@app.get("/api/places")
def fetch_places(
    category: Optional[str] = Query(None, description="Lọc theo 'an_uong', 'di_choi' hoặc 'all'"),
    min_rating: Optional[float] = Query(None, description="Điểm đánh giá tối thiểu (VD: 4.5)")
):
    """Trả về danh sách địa điểm theo bộ lọc"""
    places = get_all_places(category=category, min_rating=min_rating)
    return {
        "count": len(places),
        "places": places
    }

@app.get("/api/places/{place_id}")
def fetch_place_detail(place_id: int):
    """Trả về thông tin chi tiết một địa điểm theo ID"""
    place = get_place_by_id(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm yêu cầu")
    return place

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách chim bay theo công thức Haversine (đơn vị: km)"""
    import math
    R = 6371.0 # Bán kính Trái Đất (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def solve_tsp_nearest_neighbor(start_coord: dict, places: list) -> list:
    """
    Thuật toán tham lam (Greedy Nearest Neighbor) giải bài toán TSP:
    Bắt đầu từ điểm xuất phát, luôn luôn chọn trạm tiếp theo gần nhất chưa được ghé thăm.
    """
    if not places:
        return []
    
    unvisited = places.copy()
    ordered_route = []
    current_lat = start_coord["lat"]
    current_lon = start_coord["lon"]

    while unvisited:
        nearest_idx = 0
        min_dist = float('inf')
        for i, place in enumerate(unvisited):
            d = haversine_distance(current_lat, current_lon, place["lat"], place["lon"])
            if d < min_dist:
                min_dist = d
                nearest_idx = i

        chosen_place = unvisited.pop(nearest_idx)
        chosen_place["leg_distance_km"] = min_dist
        ordered_route.append(chosen_place)
        current_lat = chosen_place["lat"]
        current_lon = chosen_place["lon"]

    return ordered_route

from pydantic import BaseModel
class RouteOptimizeRequest(BaseModel):
    start_lat: float
    start_lon: float
    place_ids: List[int]

@app.post("/api/route/optimize")
def optimize_route(req: RouteOptimizeRequest):
    """API tối ưu hóa thứ tự ghé thăm theo thuật toán láng giềng gần nhất"""
    places_to_visit = []
    for pid in req.place_ids:
        p = get_place_by_id(pid)
        if p:
            places_to_visit.append(p)
            
    if not places_to_visit:
        raise HTTPException(status_code=400, detail="Danh sách địa điểm rỗng")

    start_coord = {"lat": req.start_lat, "lon": req.start_lon}
    optimized_stops = solve_tsp_nearest_neighbor(start_coord, places_to_visit)
    
    total_km = sum(s.get("leg_distance_km", 0.0) for s in optimized_stops)
    return {
        "start": start_coord,
        "total_distance_km": round(total_km, 2),
        "stops_count": len(optimized_stops),
        "ordered_stops": optimized_stops
    }

# Tích hợp Google Gemini AI Client
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ai_client = None
if GEMINI_KEY:
    try:
        from google import genai
        ai_client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print("Không thể khởi tạo Gemini Client:", e)
        ai_client = None

def build_ai_tour_prompt(user_pref: dict, candidate_places: list) -> str:
    """Xây dựng prompt chi tiết yêu cầu Gemini sinh lịch trình du lịch văn hóa có cấu trúc"""
    prompt = f"""
    Bạn là một chuyên gia văn hóa và hướng dẫn viên du lịch bản địa am hiểu sâu sắc Sài Gòn - Chợ Lớn.
    Người dùng muốn lập chuyến đi:
    - Thời gian rảnh: {user_pref.get('free_time', '14:00 - 18:00')}
    - Đi cùng: {user_pref.get('companion', 'bạn bè')}
    - Mục đích: {user_pref.get('purpose', 'cả hai')}
    - Ngân sách: {user_pref.get('budget', 'tiết kiệm')}
    
    Hãy chọn ra đúng 3 địa điểm thích hợp nhất từ danh sách sau:
    {json.dumps([{"name": p["name"], "cat": p["category"], "addr": p["address"]} for p in candidate_places[:15]], ensure_ascii=False)}

    Yêu cầu trả về đúng định dạng JSON:
    {{
      "trip_title": "Tên chủ đề chuyến đi",
      "cultural_story": "Lời bình văn hóa tổng quan",
      "schedule": [
        {{"time_slot": "14:00 - 15:30", "place_name": "...", "activity": "...", "tip": "..."}}
      ]
    }}
    """
    return prompt.strip()

def filter_candidates_for_context(purpose: str, companion: str) -> list:
    """Lọc các địa điểm ứng viên phù hợp với mục đích và đối tượng đi cùng"""
    all_p = get_all_places()
    candidates = []
    for p in all_p:
        if purpose == "an_uong" and p["category"] != "an_uong":
            continue
        if purpose == "di_choi" and p["category"] != "di_choi":
            continue
        candidates.append(p)
    return candidates

def parse_gemini_json_response(raw_text: str) -> dict:
    """Bóc tách và parse an toàn chuỗi JSON từ phản hồi markdown của Gemini"""
    import re
    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except Exception:
        # Tìm khối {...} đầu tiên
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Không thể trích xuất JSON hợp lệ từ phản hồi AI")

# Enrich commentary with local insider tips
AI_CULTURAL_TIPS = {
    "Chùa Bà Thiên Hậu": "Hãy thắp vòng nhang treo trần để cầu bình an và chiêm ngưỡng gốm men Cây Mai.",
    "Hội Quán Nghĩa An": "Nổi tiếng với tượng ngựa Xích Thố và nghệ thuật chạm khắc gỗ sơn son thếp vàng.",
    "Hủ Tiếu Sa Tế Quảng Ký": "Nên gọi tô thập cẩm kèm bánh mì để chấm nước dùng sa tế đậu phộng gia truyền béo ngậy.",
    "Sủi Cảo Thiên Thiên": "Gọi sủi cảo chiên giòn và sủi cảo mực ngâm tro đặc trưng phố Hà Tôn Quyền."
}

class ItineraryGenRequest(BaseModel):
    free_time: Optional[str] = "14:00 - 18:30"
    companion: Optional[str] = "ban_be"
    purpose: Optional[str] = "ca_hai"
    budget: Optional[str] = "thoai_mai"

@app.post("/api/itinerary/generate")
def generate_ai_itinerary(req: ItineraryGenRequest):
    """Endpoint sinh lộ trình thông minh kết hợp Gemini AI và offline fallback"""
    candidates = filter_candidates_for_context(req.purpose, req.companion)
    if ai_client:
        try:
            prompt = build_ai_tour_prompt(req.dict(), candidates)
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            result = parse_gemini_json_response(response.text)
            return {"source": "gemini_ai", "itinerary": result}
        except Exception as e:
            print("[WARN] Gemini AI call failed, switching to heuristic fallback:", e)
            
    # Fallback heuristic generator
    return {"source": "heuristic_fallback", "itinerary": generate_heuristic_itinerary(req.dict(), candidates)}

def generate_heuristic_itinerary(pref: dict, candidates: list) -> dict:
    """Bộ máy heuristic thông minh sinh lịch trình 3 trạm chuẩn mực văn hóa Chợ Lớn"""
    import random
    heritages = [c for c in candidates if c["category"] == "di_choi"] or candidates[:2]
    foods = [c for c in candidates if c["category"] == "an_uong"] or candidates[2:4]

    stop1 = heritages[0] if heritages else candidates[0]
    stop2 = heritages[1] if len(heritages) > 1 else (foods[0] if foods else candidates[1])
    stop3 = foods[0] if foods else candidates[-1]

    return {
        "trip_title": "Dạo Bước Di Sản & Ẩm Thực Chợ Lớn Trứ Danh",
        "cultural_story": "Hành trình kết nối chiều sâu văn hóa tâm linh của các hội quán cổ và tinh hoa ẩm thực ẩm thực người Hoa Quận 5.",
        "schedule": [
            {
                "time_slot": "14:30 - 15:45",
                "place_name": stop1["name"],
                "activity": "Tham quan chiêm bái, ngắm kiến trúc phù điêu gốm men Cây Mai",
                "tip": AI_CULTURAL_TIPS.get(stop1["name"], "Giữ trật tự trang nghiêm khi vào chánh điện.")
            },
            {
                "time_slot": "16:00 - 17:15",
                "place_name": stop2["name"],
                "activity": "Check-in kiến trúc cổ và tìm hiểu các câu chuyện lập nghiệp",
                "tip": AI_CULTURAL_TIPS.get(stop2["name"], "Nên chụp góc nghiêng để lấy toàn cảnh mái ngói âm dương.")
            },
            {
                "time_slot": "17:30 - 19:00",
                "place_name": stop3["name"],
                "activity": "Thưởng thức ẩm thực trứ danh buổi chiều tối",
                "tip": AI_CULTURAL_TIPS.get(stop3["name"], "Hỏi người phục vụ món signature của quán.")
            }
        ]
    }

def clean_markdown_tokens(text: str) -> str:
    """Loại bỏ các ký tự markdown thừa khỏi lời bình của Gemini"""
    import re
    cleaned = re.sub(r"[*_#`]", "", text)
    return cleaned.strip()

from backend.database import register_user, authenticate_user

class AuthLoginRequest(BaseModel):
    username: str
    password: str

class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str

@app.post("/api/auth/login")
def login(req: AuthLoginRequest):
    """Đăng nhập tài khoản và trả về profile người dùng"""
    user, err = authenticate_user(req.username, req.password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"message": "Đăng nhập thành công", "user": user}

@app.post("/api/auth/register")
def register(req: AuthRegisterRequest):
    """Đăng ký tài khoản người dùng mới"""
    user, err = register_user(req.username, req.password, req.full_name)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"message": "Đăng ký thành công", "user": user}

def verify_admin_role(user_role: str):
    """Kiểm tra quyền hạn quản trị viên trước khi thực hiện thao tác quản trị"""
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ có quản trị viên mới có quyền thao tác")

from backend.database import add_place

class CreatePlaceRequest(BaseModel):
    name: str
    category: str
    address: str
    district: Optional[str] = "Quận 5"
    lat: float
    lon: float
    open_time: Optional[str] = "08:00"
    close_time: Optional[str] = "22:00"
    min_price: Optional[int] = 30000
    max_price: Optional[int] = 100000
    rating: Optional[float] = 4.5
    image_url: Optional[str] = None
    tags: Optional[str] = "nhom_ban"

@app.post("/api/admin/places")
def create_place(req: CreatePlaceRequest):
    """Thêm địa điểm mới (Dành cho Admin)"""
    new_id = add_place(req.dict())
    return {"message": "Thêm địa điểm thành công", "place_id": new_id}

from backend.database import update_place, delete_place

@app.put("/api/admin/places/{place_id}")
def edit_place(place_id: int, req: CreatePlaceRequest):
    """Cập nhật địa điểm theo ID (Dành cho Admin)"""
    ok = update_place(place_id, req.dict())
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm để sửa")
    return {"message": "Cập nhật thành công"}

@app.delete("/api/admin/places/{place_id}")
def remove_place(place_id: int):
    """Xóa địa điểm theo ID (Dành cho Admin)"""
    ok = delete_place(place_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm để xóa")
    return {"message": "Đã xóa địa điểm thành công"}

def extract_coords_from_gmaps_url(url: str):
    """Trích xuất tọa độ lat, lon từ liên kết Google Maps dạng share hoặc tìm kiếm"""
    import re
    # Kiểu 1: @10.75338,106.65997
    match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if match:
        return float(match.group(1)), float(match.group(2))
    
    # Kiểu 2: ?q=10.75338,106.65997 hoặc ll=...
    match2 = re.search(r"[?&](?:q|ll)=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if match2:
        return float(match2.group(1)), float(match2.group(2))
        
    return None, None

class GmapsExtractRequest(BaseModel):
    url: str

@app.post("/api/admin/extract-gmaps")
def api_extract_gmaps(req: GmapsExtractRequest):
    """Bóc tách tọa độ tự động từ link Google Maps để điền form nhanh"""
    lat, lon = extract_coords_from_gmaps_url(req.url)
    if not lat or not lon:
        raise HTTPException(status_code=400, detail="Không thể trích xuất tọa độ từ liên kết cung cấp")
    return {"lat": lat, "lon": lon}

from backend.database import toggle_favorite, get_user_favorites

class FavoriteToggleRequest(BaseModel):
    user_id: int
    place_id: int

@app.post("/api/favorites/toggle")
def api_toggle_favorite(req: FavoriteToggleRequest):
    """Bật/tắt trạng thái yêu thích địa điểm của người dùng"""
    is_saved = toggle_favorite(req.user_id, req.place_id)
    return {"place_id": req.place_id, "is_saved": is_saved}

@app.get("/api/favorites")
def api_get_favorites(user_id: int):
    """Lấy danh sách địa điểm yêu thích theo user_id"""
    favs = get_user_favorites(user_id)
    return {"count": len(favs), "favorites": favs}
