# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sggo.db")

def check():
    if not os.path.exists(DB_PATH):
        print("Database not found! Run database.py first.")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM places")
    p_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users")
    u_count = cur.fetchone()[0]
    print(f"[OK] Database Status: {p_count} places, {u_count} users loaded.")
    conn.close()

if __name__ == "__main__":
    check()

def test_fallback():
    from backend.main import generate_heuristic_itinerary, get_all_places
    places = get_all_places()
    itin = generate_heuristic_itinerary({"free_time": "14:00 - 18:00"}, places)
    assert len(itin["schedule"]) == 3
    print("[PASS] Fallback itinerary generation verified with 3 stops.")

if __name__ == "__main__":
    test_fallback()
