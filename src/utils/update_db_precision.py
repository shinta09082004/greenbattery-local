import sqlite3
db_path = "data/project.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

new_candidates = [
    ("新庄市本合海 (国道47号路肩)", 38.74530, 140.22485, "国道沿いの山林。送電線直下かつ路肩3m以内。完全非農地。"),
    ("大蔵村大字清水 (県道沿い原野)", 38.72485, 140.24580, "変電所至近の広大な原野。道路沿いでアクセス抜群。"),
    ("真室川町木ノ下 (鉄塔下荒地)", 38.86860, 140.22440, "送電鉄塔至近。道路沿いの平坦な未利用地。")
]

for name, lat, lon, memo in new_candidates:
    g_map = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    mapple = f"https://labs.mapple.com/mapplexml.html#18/{lat}/{lon}"
    cursor.execute('''
        INSERT INTO properties (area_name, latitude, longitude, google_maps_url, mapple_url, memo, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, lat, lon, g_map, mapple, memo, "厳選済み"))

conn.commit()
conn.close()
print("CEO飯田: 究極の3地点をDBに追記しました。")
