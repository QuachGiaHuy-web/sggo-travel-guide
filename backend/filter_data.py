import json
import os

INPUT_FILE = "export.geojson"
OUTPUT_FILE = "test_places_q5.json"

def extract_coordinates(feature):
    geometry = feature.get("geometry") or {}
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    
    if not coords:
        return None, None
        
    if gtype == "Point":
        return coords[0], coords[1]
    
    # Đối với Polygon hoặc MultiPolygon (chợ, công viên, khối tòa nhà)
    if gtype == "Polygon" and len(coords) > 0 and len(coords[0]) > 0:
        ring = coords[0]
        avg_lon = sum(pt[0] for pt in ring) / len(ring)
        avg_lat = sum(pt[1] for pt in ring) / len(ring)
        return avg_lon, avg_lat
        
    return None, None

def classify_category(props):
    amenity = props.get("amenity", "")
    tourism = props.get("tourism", "")
    shop = props.get("shop", "")
    craft = props.get("craft", "")

    # Phân loại homestay / khách sạn
    if tourism in ["hotel", "motel", "hostel", "guest_house", "apartment", "chalet"]:
        return "homestay"
    
    # Phân loại workshop / tô tượng / nghệ thuật
    if shop in ["craft", "pottery", "art", "photo"] or craft in ["pottery", "ceramic", "handicraft"]:
        return "workshop"

    # Phân loại ăn uống
    if amenity in ["restaurant", "cafe", "fast_food", "food_court", "ice_cream", "bar", "pub", "biergarten"]:
        return "an_uong"

    # Tất cả các nhóm giải trí, tâm linh, mua sắm
    return "di_choi"

def clean_and_filter():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Không tìm thấy file '{INPUT_FILE}' trong thư mục backend!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    features = raw_data.get("features", [])
    valid_places = []

    print(f"🔍 Đang phân tích và xử lý {len(features)} đối tượng từ OSM...")

    for item in features:
        props = item.get("properties", {})
        name = props.get("name")

        lon, lat = extract_coordinates(item)

        # Lọc chỉ lấy địa điểm có tên thật và có tọa độ chuẩn
        if name and len(name.strip()) > 1 and lon is not None and lat is not None:
            category = classify_category(props)
            osm_type = props.get("amenity") or props.get("tourism") or props.get("leisure") or props.get("shop") or "place"
            street = props.get("addr:street", "")

            valid_places.append({
                "name": name.strip(),
                "category": category,
                "osm_type": osm_type,
                "lat": round(lat, 7),
                "lon": round(lon, 7),
                "street": street.strip(),
                "district": "Quận 5"
            })

    # Khử trùng lặp tên quán
    unique_places = []
    seen_names = set()
    for p in valid_places:
        clean_name = p["name"].lower()
        if clean_name not in seen_names:
            seen_names.add(clean_name)
            unique_places.append(p)

    print(f"✅ Đã lọc thành công {len(unique_places)} địa điểm thực tế, không trùng lặp tại Quận 5!")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_places, f, ensure_ascii=False, indent=2)

    print(f"🎉 Đã lưu file chuẩn hóa '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    clean_and_filter()