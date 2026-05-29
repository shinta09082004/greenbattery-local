import sqlite3
import csv
import os

def generate_wilderness_5():
    # CEO飯田による「原野・山林」厳選5地点
    # 選定基準: 送電線沿い、民家なし、かつ「畑・田」ではない未利用地
    candidates = [
        {"id": 1, "area": "新庄市/真室川町境界付近（山林）", "lat": 38.8415, "lon": 140.2685, "reason": "送電線が山林を抜けるポイント。広大な未利用地。"},
        {"id": 2, "area": "大蔵村 西部山際（原野）", "lat": 38.6450, "lon": 140.1250, "reason": "集落から離れた斜面下の平坦な原野。高圧線至近。"},
        {"id": 3, "area": "真室川町 南部（荒地）", "lat": 38.8655, "lon": 140.2215, "reason": "かつての作業場跡か。周囲が木々に囲まれた隔離地。"},
        {"id": 4, "area": "新庄市 東部山麓（泉田山）", "lat": 38.8185, "lon": 140.3455, "reason": "山林の入り口。送電鉄塔のすぐそば。"},
        {"id": 5, "area": "新庄市 南西境界（山林）", "lat": 38.7180, "lon": 140.2355, "reason": "変電所から山側へ延びる送電線直下の斜面。"}
    ]
    
    db_path = "data/project.db"
    csv_path = "data/processed/candidates/wilderness_5_candidates.csv"
    
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
    path = generate_wilderness_5()
    print(f"CEO飯田: 原野・山林特化の5地点を生成しました: {path}")
