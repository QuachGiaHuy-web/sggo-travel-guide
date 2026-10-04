import json

with open("test_places_q5.json", "r", encoding="utf-8") as f:
    places = json.load(f)

print(f"📊 TỔNG SỐ ĐỊA ĐIỂM: {len(places)}")

# Thống kê theo phân loại
stats = {}
for p in places:
    cat = p.get("category", "khac")
    stats[cat] = stats.get(cat, 0) + 1

print("\n--- PHÂN BỔ DANH MỤC ---")
for cat, count in stats.items():
    print(f"• {cat}: {count} địa điểm")

# Thử tìm một số địa danh đặc trưng của Quận 5
famous_keywords = [
    "sủi cảo", "chè", "bình tây", "an đông", "hùng vương", 
    "thiên hậu", "bà thiên hậu", "hội quán", "phở", "dimsum", "cinema", "cgv"
]

print("\n--- KIỂM TRA ĐỊA DANH ĐẶC TRƯNG QUẬN 5 CÓ TRONG DỮ LIỆU ---")
found_count = 0
for kw in famous_keywords:
    matches = [p["name"] for p in places if kw in p["name"].lower()]
    if matches:
        found_count += 1
        print(f"✔ Từ khóa '{kw}': tìm thấy {len(matches)} điểm (vd: {matches[0]})")
    else:
        print(f"✖ Từ khóa '{kw}': chưa thấy xuất hiện tên trực tiếp")