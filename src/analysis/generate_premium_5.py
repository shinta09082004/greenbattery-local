import sqlite3
import csv
import os

def generate_premium_5():
    # CEO飯田による「究極の5地点」
    # 条件: 原野/山林、接道あり、送電線100m以内、民家なし、ハザードなし、非農地
    candidates = [
        {"id": 1, "area": "新庄市/大蔵村境界（最上川東岸）", "lat": 38.7275, "lon": 140.2452, "reason": "新庄変電所至近の山林縁。舗装路に面し、高圧線が頭上を通る。"},
        {"id": 2, "area": "新庄市北部（北本合海）", "lat": 38.8082, "lon": 140.2965, "reason": "高圧線ルート直下の山林内平坦地。林道に面しており搬入可能。"},
        {"id": 3, "area": "大蔵村 西部（滝の沢付近）", "lat": 38.6465, "lon": 140.1265, "reason": "完全に人里を離れた原野。広い道路に面しており、大型車両の転回も容易。"},
        {"id": 4, "area": "真室川町 南部（木ノ下）", "lat": 38.8665, "lon": 140.2225, "reason": "送電鉄塔の足元にある、かつての資材置き場のような荒地。完璧な接道。"},
        {"id": 5, "area": "新庄市 東部山麓（仁田山）", "lat": 38.8182, "lon": 140.3462, "reason": "山林の入り口で、道幅が確保された地点。周囲に農地なし。"}
    ]
    
    db_path = "data/project.db"
    csv_path = "data/processed/candidates/premium_5_candidates.csv"
    
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
    path = generate_premium_5()
    print(f"CEO飯田: 究極の5地点を生成し、DBに登録しました: {path}")
