# main.py
import os
import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from data_places import MOCK_PLACES

app = FastAPI(title="SGGo API Backend")

# Cho phép Frontend gọi API qua CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Gemini Client (Đọc từ biến môi trường GEMINI_API_KEY)
client = genai.Client(api_key="AQ.Ab8RN6K6DhBORk5YoIPhngds_Lc4da6Pn7gHdg7r6lM4vd4eZw")

class ItineraryRequest(BaseModel):
    start_location: str
    free_time: str
    context: str
    budget: str

@app.get("/api/places")
def get_places(
    category: str = Query(None),
    context: str = Query(None),
    price_level: int = Query(None)
):
    """API lấy danh sách địa điểm có hỗ trợ lọc đa tiêu chí"""
    results = MOCK_PLACES
    if category and category != "all":
        results = [p for p in results if p["category"] == category]
    if context and context != "all":
        results = [p for p in results if p["context"] == context]
    if price_level:
        results = [p for p in results if p["price_level"] == price_level]
    return {"total": len(results), "data": results}

@app.post("/api/ai-itinerary")
def generate_itinerary(req: ItineraryRequest):
    """API tạo lịch trình thông minh không đi ngược đường dùng Gemini"""
    # Lấy nhanh 15 địa điểm mẫu khớp ngữ cảnh làm context đưa vào prompt
    candidate_places = [p for p in MOCK_PLACES if p["context"] == req.context][:15]
    
    prompt = f"""
    Bạn là chuyên gia gợi ý lịch trình vui chơi tại TP.HCM.
    Người dùng có yêu cầu:
    - Điểm xuất phát: {req.start_location}
    - Khung giờ: {req.free_time}
    - Đi cùng: {req.context} (nguoi_yeu: hẹn hò, nhom_ban: náo nhiệt, gia_dinh: ấm cúng)
    - Ngân sách: {req.budget}

    Dưới đây là danh sách các địa điểm khả dụng:
    {json.dumps(candidate_places, ensure_ascii=False)}

    Nhiệm vụ:
    1. Chọn ra đúng 2-3 địa điểm hợp lý (1 quán ăn/uống và 1 điểm chơi/chill).
    2. Sắp xếp theo tuyến đường tối ưu để KHÔNG BỊ ĐI NGƯỢC ĐƯỜNG giữa các quận.
    3. Ước tính thời gian di chuyển bằng xe máy giữa các điểm và cảnh báo nếu rơi vào khung giờ cao điểm (17:00 - 19:00).

    Trả về đúng cấu trúc JSON sau (không kèm markdown format ngoài):
    {{
      "summary": "Tóm tắt ngắn lộ trình",
      "steps": [
        {{
          "time": "15:00 - 15:20",
          "action": "Di chuyển từ điểm xuất phát đến Điểm 1",
          "location": "Tên điểm",
          "travel_info": "Thời gian và khoảng cách dự kiến",
          "traffic_warning": "Cảnh báo kẹt xe nếu có"
        }}
      ]
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        # Fallback dữ liệu tĩnh nếu chưa set API Key
        return {
            "summary": "Lộ trình tối ưu (Chế độ dự phòng offline)",
            "steps": [
                {
                    "time": "15:00 - 15:20",
                    "action": f"Xuất phát từ {req.start_location}",
                    "location": candidate_places[0]["name"],
                    "travel_info": "15 phút xe máy (~4.2 km)",
                    "traffic_warning": "Đường thoáng, di chuyển thuận lợi"
                },
                {
                    "time": "15:20 - 17:30",
                    "action": "Thưởng thức cafe & không gian chill",
                    "location": candidate_places[0]["name"],
                    "travel_info": "Tại điểm đến",
                    "traffic_warning": "Chuẩn bị vào giờ cao điểm lúc 17:30"
                },
                {
                    "time": "17:45 - 19:30",
                    "action": "Ăn tối lãng mạn/vui vẻ",
                    "location": candidate_places[1]["name"],
                    "travel_info": "8 phút di chuyển (cách 1.2km)",
                    "traffic_warning": "Giờ cao điểm: Khuyến nghị đi hẻm thông thoáng"
                }
            ]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)