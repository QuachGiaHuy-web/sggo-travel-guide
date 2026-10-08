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
