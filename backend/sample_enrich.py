import json

with open("test_places_q5.json", "r", encoding="utf-8") as f:
    places = json.load(f)

# Lấy 20 địa điểm đại diện đủ các nhóm (ăn uống, đi chơi, hội quán, dimsum...)
sample = places[:20]

with open("test_20_places.json", "w", encoding="utf-8") as f:
    json.dump(sample, f, ensure_ascii=False, indent=2)

print(f"Đã tạo file test_20_places.json gồm {len(sample)} địa điểm sẵn sàng nạp cho Tampermonkey!")