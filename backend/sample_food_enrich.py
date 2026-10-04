import json

with open("test_places_q5.json", "r", encoding="utf-8") as f:
    places = json.load(f)

# Lấy 20 quán ăn uống và workshop
sample_food = [p for p in places if p.get("category") in ["an_uong", "workshop"]][:20]

with open("test_20_food.json", "w", encoding="utf-8") as f:
    json.dump(sample_food, f, ensure_ascii=False, indent=2)

print("Đã tạo xong file test_20_food.json!")