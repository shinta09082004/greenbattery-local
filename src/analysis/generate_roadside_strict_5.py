import sqlite3
import csv
import os

def generate_roadside_strict_5():
    # CEO飯田による「路肩直結」厳選5地点
    # 条件: 道路から10m以内、原野/山林、送電線100m以内、民家なし、非農地
    candidates = [
        {"id": 1, "area": "大蔵村合海（新庄変電所南側・路肩）", "lat": 38.72658, "lon": 140.24475, "reason": "道路のすぐ脇。変電所至近で送電線が道路を跨ぐポイント。"},
        {"id": 2, "area": "真室川町木ノ下（路肩荒地）", "lat": 38.86718, "lon": 140.22355, "reason": "送電鉄塔の直下かつ道路の目の前。搬入に最適な平坦な荒地。"},
        {"id": 3, "area": "新庄市本合海（路肩高台）", "lat": 38.74592, "lon": 140.22598, "reason": "主要地方道沿い。道路から一段上がった平坦な山林縁。"},
        {"id": 4, "area": "新庄市野口（北新庄駅北側・路肩）", "lat": 38.80755, "lon": 140.29705, "reason": "鉄道と道路に挟まれた、送電線沿いの帯状の原野。"},
        {"id": 5, "area": "大蔵村滝の沢（山間道路沿い）", "lat": 38.64702, "lon": 140.12745, "reason": "山林の中を通る広い道路の路肩。周囲に全く民家なし。"}
    ]
    
    db_path = "data/project.db"
    csv_path = "data/processed/candidates/roadside_strict_5_candidates.csv"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    output_data = []
    
    for c in candidates:
        g_map = f"https://www.google.com/maps/search/?api=1&query={c['lat']},{c['lon']}"
        g_sat = f"https://www.google.com/maps/search/?api=1&query={c['lat']},{c['lon']}&basemap=satellite"
        mapple = f"https://labs.mapple.com/mapplexml.html#18/{c['lat']}/{c['lon']}"
        
        cursor.execute('''
            INSERT INTO properties (area_name, latitude, longitude, google_maps_url, mapple_url, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (c['area'], c['lat'], c['lon'], g_map, mapple, c['reason']))
        
        output_data.append([
            c['id'], c['area'], c['lat'], c['lon'], g_map, g_sat, mapple, c['reason']
        ])
        
    conn.commit()
    conn.close()
    
    header = ["ID", "エリア", "緯度", "経度", "Googleマップ", "航空写真", "Mappleリンク", "選定理由"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(output_data)
        
    return csv_path

if __name__ == "__main__":
    path = generate_roadside_strict_5()
    print(f"CEO飯田: 路肩直結の5地点を生成しました: {path}")
