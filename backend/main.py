import os
import json
import math
import unicodedata
import urllib.request
import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Tự động đọc file .env bằng thư viện chuẩn có sẵn của Python (không cần pip install)
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

app = FastAPI(title="SGGo! Backend API")

# Mở CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nạp 40 địa điểm thật từ file enriched_places.json
DATA_FILE = os.path.join(os.path.dirname(__file__), "enriched_places.json")

def load_places():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

PLACES_DB = load_places()

# Lấy key từ file .env vừa nạp
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

ai_client = None
if GEMINI_KEY:
    try:
        from google import genai
        ai_client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"Lỗi khởi tạo AI Client: {e}")

class ItineraryRequest(BaseModel):
    start_location: str
    free_time: str
    context: str
    budget: Optional[str] = "Vừa vặn thoải mái"

def remove_accent(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để so khớp chuỗi"""
    text = unicodedata.normalize('NFD', text)
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn').lower()

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách bề mặt Trái Đất giữa 2 tọa độ GPS (km)"""
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
    Xác định tọa độ GPS của BẤT KỲ ĐỊA ĐIỂM NÀO ở TP.HCM/Việt Nam qua OpenStreetMap Nominatim.
    Không cần key, hoàn toàn miễn phí.
    """
    loc_clean = location_str.strip()
    
    # 1. Gọi Geocoding Nominatim
    try:
        query = f"{loc_clean}, Ho Chi Minh City, Vietnam"
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "limit": 1
        })
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "SGGo-Travel-Guide-D5/1.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return (lat, lon)
    except Exception as e:
        print(f"[Geocoding Error] Lỗi lấy tọa độ từ Nominatim: {e}")

    # 2. Bảng tọa độ dự phòng các điểm lớn tại TP.HCM
    CITY_LANDMARKS = {
        "ben thanh": (10.7725, 106.6980),
        "pho di bo": (10.7740, 106.7030),
        "ho con rua": (10.7828, 106.6958),
        "san bay": (10.8185, 106.6588),
        "tan son nhat": (10.8185, 106.6588),
        "landmark 81": (10.7950, 106.7219),
        "thu duc": (10.8500, 106.7600),
        "go vap": (10.8388, 106.6653),
        "binh thanh": (10.8105, 106.7091),
        "tan binh": (10.7938, 106.6547),
        "su pham": (10.7614, 106.6822),
        "nowzone": (10.7633, 106.6822),
        "an dong": (10.7553, 106.6704),
        "cho lon": (10.7525, 106.6542),
    }
    clean_no_acc = remove_accent(loc_clean)
    for k, v in CITY_LANDMARKS.items():
        if k in clean_no_acc:
            return v

    return (10.7769, 106.7009)

def optimize_route_nearest_neighbor(start_coords, candidate_places: List[dict], max_stops=3):
    """Thuật toán định tuyến Nearest Neighbor xếp các điểm gần nhau nhất liên tiếp"""
    unvisited = [p.copy() for p in candidate_places if p.get("lat") and p.get("lon")]
    current_lat, current_lon = start_coords
    route = []

    for _ in range(min(max_stops, len(unvisited))):
        nearest_node = None
        min_distance = float("inf")

        for p in unvisited:
            dist = calculate_haversine_distance(current_lat, current_lon, p["lat"], p["lon"])
            if dist < min_distance:
                min_distance = dist
                nearest_node = p

        if nearest_node:
            nearest_node["dist_km"] = round(min_distance, 2)
            travel_minutes = max(3, int(min_distance * 3.5))
            nearest_node["travel_minutes"] = travel_minutes
            
            route.append(nearest_node)
            current_lat, current_lon = nearest_node["lat"], nearest_node["lon"]
            unvisited.remove(nearest_node)

    return route

@app.get("/")
def read_root():
    return {"status": "ok", "total_places": len(PLACES_DB)}

@app.get("/api/places")
def get_places(category: Optional[str] = None):
    if category and category != "all":
        return [p for p in PLACES_DB if p.get("category") == category]
    return PLACES_DB

@app.get("/api/stats")
def get_stats():
    total = len(PLACES_DB)
    verified = sum(1 for p in PLACES_DB if p.get("is_verified"))
    return {
        "total_places": total,
        "verified_places": verified,
        "unverified_places": total - verified
    }

@app.post("/api/ai-itinerary")
def generate_itinerary(req: ItineraryRequest):
    if not PLACES_DB:
        raise HTTPException(status_code=500, detail="Cơ sở dữ liệu rỗng.")

    # 1. Xác định tọa độ điểm xuất phát ở bất kỳ đâu
    start_lat, start_lon = resolve_start_coords(req.start_location)

    # 2. Lọc ứng viên theo bối cảnh
    ctx_clean = remove_accent(req.context)
    if "an" in ctx_clean or "uong" in ctx_clean:
        candidates = [p for p in PLACES_DB if p.get("category") == "an_uong"]
    elif "choi" in ctx_clean or "chill" in ctx_clean:
        candidates = [p for p in PLACES_DB if p.get("category") in ["di_choi", "workshop"]]
    else:
        candidates = PLACES_DB

    if len(candidates) < 3:
        candidates = PLACES_DB

    # 3. Thuật toán định tuyến tìm 3 trạm dừng liên hoàn thuận đường nhất
    optimized_stops = optimize_route_nearest_neighbor((start_lat, start_lon), candidates, max_stops=3)

    if not optimized_stops:
        raise HTTPException(status_code=500, detail="Không tìm được địa điểm phù hợp.")

    time_schedule = [
        ("15:00 - 16:30", "Chặng 1: Khởi động"),
        ("16:45 - 18:30", "Chặng 2: Trải nghiệm trọng tâm"),
        ("18:45 - 20:30", "Chặng 3: Kết thúc trọn vẹn")
    ]

    steps = []
    for idx, spot in enumerate(optimized_stops):
        slot_time, default_action = time_schedule[idx] if idx < len(time_schedule) else ("20:30+", "Điểm đến")
        dist = spot["dist_km"]
        t_min = spot["travel_minutes"]
        addr = spot.get("full_address") or f"{spot.get('street', 'Quận 5')}, TP.HCM"
        rating_str = f"⭐ {spot.get('rating')} ({spot.get('reviews_count')} đánh giá)" if spot.get("is_verified") else ""

        if dist < 1.0:
            traffic_note = "Rất gần điểm trước, di chuyển thuận chiều, không lo quay đầu xe."
        elif dist < 3.0:
            traffic_note = "Tuyến đường ngắn trong khu vực, chú ý đèn đỏ tại các ngã tư."
        else:
            traffic_note = f"Khoảng cách từ điểm xuất phát vào Quận 5 (~{dist} km), nên đi sớm tránh giờ tan tầm."

        steps.append({
            "time": slot_time,
            "action": f"{default_action} [{spot.get('category', 'Khám phá')}]",
            "location": f"{spot['name']} — {addr} {rating_str}".strip(),
            "travel_info": f"Di chuyển ~{dist} km (khoảng {t_min} phút xe máy)",
            "traffic_warning": traffic_note
        })

    summary_text = (
        f"Lộ trình xuất phát từ '{req.start_location}', "
        f"tối ưu thứ tự 3 điểm dừng theo khoảng cách GPS thực tế tại Quận 5, phù hợp bối cảnh {req.context}."
    )

    # 4. Viết tóm tắt bằng Gemini
    if ai_client:
        try:
            stops_names = ", ".join([s['name'] for s in optimized_stops])
            prompt = (
                f"Người dùng xuất phát từ '{req.start_location}', bối cảnh '{req.context}'. "
                f"Các điểm đến theo thứ tự: {stops_names}. "
                f"Hãy viết một câu tóm tắt thật cuốn hút giới thiệu lịch trình này."
            )
            res = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if res.text:
                summary_text = res.text.strip()
        except Exception:
            try:
                res = ai_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                if res.text:
                    summary_text = res.text.strip()
            except Exception:
                pass

    return {
        "summary": summary_text,
        "steps": steps
    }