import json
import os

filename = "export.geojson"

if not os.path.exists(filename):
    print(f"Lỗi: Không tìm thấy file {filename} trong thư mục hiện tại!")
    exit()

with open(filename, "r", encoding="utf-8") as f:
    data = json.load(f)

places = []
features = data.get("features", [])

for item in features:
    props = item.get("properties", {})
    geometry = item.get("geometry", {})
    coords = geometry.get("coordinates", [])

    name = props.get("name")
    
    # Chỉ lấy các địa điểm có tên cụ thể
    if name and len(name.strip()) > 1 and len(coords) >= 2:
        lon, lat = coords[0], coords[1]
        
        # Phân loại cơ bản ban đầu
        is_entertainment = bool(props.get("tourism") or props.get("leisure"))
        category = "di_choi" if is_entertainment else "an_uong"
        
        osm_type = props.get("amenity") or props.get("tourism") or props.get("leisure") or "venue"
        street = props.get("addr:street", "")

        places.append({
            "name": name.strip(),
            "category": category,
            "osm_type": osm_type,
            "lat": lat,
            "lon": lon,
            "street": street
        })

print(f"Tổng số địa điểm hợp lệ tìm thấy: {len(places)}")

# Trích xuất 30 quán đầu tiên làm bộ dữ liệu thử nghiệm
test_subset = places[:30]
output_file = "test_places.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(test_subset, f, ensure_ascii=False, indent=2)

print(f"Đã lưu thành công 30 địa điểm vào '{output_file}' để sẵn sàng cho Tampermonkey!")