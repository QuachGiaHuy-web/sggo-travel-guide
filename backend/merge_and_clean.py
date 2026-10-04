import json
import os

BATCH1_FILE = "enriched_places_batch1.json"
BATCH2_FILE = "enriched_food_batch2.json"
OUTPUT_FILE = "enriched_places.json"

def clean_record(place):
    addr = place.get("full_address", "")
    reviews = place.get("reviews_count", 0)
    rating = place.get("rating")

    # Kiểm tra địa chỉ có hợp lệ hay không:
    # Không lấy nếu là địa chỉ chung chung, hoặc bị dính địa chỉ của Chợ Thiếc (129 Phó Cơ Điều) do lỗi ghost data
    is_valid_addr = bool(
        addr 
        and addr != "Quận 5, TP.HCM"
        and not addr.endswith("Quận 5, TP.HCM")
        and "129 Phó Cơ Điều" not in addr
        and not addr.startswith("+84")
        and not addr.startswith("0")
        and "mở cửa" not in addr.lower()
    )

    # Nếu địa điểm cào thành công thật sự (có địa chỉ chi tiết rõ ràng và có đánh giá)
    if is_valid_addr and reviews > 0:
        return {
            **place,
            "rating": rating,
            "reviews_count": reviews,
            "full_address": addr,
            "is_verified": True
        }

    # Nếu chưa cào được hoặc dữ liệu lỗi/chưa xác thực -> chuyển về null
    return {
        **place,
        "rating": None,
        "reviews_count": None,
        "full_address": None,
        "is_verified": False
    }

def main():
    merged_dict = {}

    for file_name in [BATCH1_FILE, BATCH2_FILE]:
        if not os.path.exists(file_name):
            print(f"⚠️️ Cảnh báo: Không tìm thấy file {file_name}")
            continue

        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            cleaned = clean_record(item)
            merged_dict[cleaned["name"]] = cleaned

    results = list(merged_dict.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    verified_count = sum(1 for p in results if p["is_verified"])
    unverified_count = len(results) - verified_count

    print(f"Tổng hợp thành công {len(results)} địa điểm vào '{OUTPUT_FILE}':")
    print(f"  • Đã xác thực (Verified): {verified_count} địa điểm")
    print(f"  • Chưa xác thực (Chờ sửa tay/cào sau): {unverified_count} địa điểm")

if __name__ == "__main__":
    main()