import sqlite3
import csv
import os

def generate_serious_10():
    # CEO飯田による厳選10地点（新庄市および周辺）
    # 選定基準: 変電所付近、主要幹線沿い、かつ住宅密集地を避けた地点
    candidates = [
        {"id": 1, "area": "新庄市/大蔵村境界", "lat": 38.7289, "lon": 140.2461, "reason": "新庄変電所(275kV)直近。送電インフラの要。"},
        {"id": 2, "area": "新庄市西部（福田）", "lat": 38.7582, "lon": 140.2745, "reason": "工業団地付近。接道が広く、建物から離隔あり。"},
        {"id": 3, "area": "新庄市北部（十日町）", "lat": 38.8055, "lon": 140.2982, "reason": "市街地北端。高圧線沿いの原野・雑種地。"},
        {"id": 4, "area": "新庄市南部（鳥越）", "lat": 38.7150, "lon": 140.2955, "reason": "バイパス付近。開発の余地がある平地。"},
        {"id": 5, "area": "新庄市西部（本合海）", "lat": 38.7455, "lon": 140.2252, "reason": "河川付近の高台。建物が少なく平坦。"},
        {"id": 6, "area": "新庄市東部（泉田）", "lat": 38.8250, "lon": 140.3150, "reason": "泉田駅北東。鉄道・送電線に近接。"},
        {"id": 7, "area": "新庄市中心郊外（金沢）", "lat": 38.7665, "lon": 140.3155, "reason": "金沢変電所から一定の距離を保った平地。"},
        {"id": 8, "area": "新庄市南西部", "lat": 38.7402, "lon": 140.2812, "reason": "主要道路交差点付近。アクセス良好。"},
        {"id": 9, "area": "大蔵村（合海）", "lat": 38.7255, "lon": 140.2415, "reason": "変電所南側の広大な平地エリア。"},
        {"id": 10, "area": "真室川町境界（北新庄）", "lat": 38.8450, "lon": 140.2750, "reason": "真室川町への入口。送電網の通り道。"}
    ]
    
    db_path = "data/project.db"
    csv_path = "data/processed/candidates/serious_10_candidates.csv"
    os.makedirs("data/processed/candidates", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    output_data = []
    
    for c in candidates:
        g_map = f"https://www.google.com/maps/search/?api=1&query={c['lat']},{c['lon']}"
        g_sat = f"https://www.google.com/maps/search/?api=1&query={c['lat']},{c['lon']}&basemap=satellite"
        mapple = f"https://labs.mapple.com/mapplexml.html#18/{c['lat']}/{c['lon']}"
        
        # DB登録
        cursor.execute('''
            INSERT INTO properties (area_name, latitude, longitude, google_maps_url, mapple_url, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (c['area'], c['lat'], c['lon'], g_map, mapple, c['reason']))
        
        output_data.append([
            c['id'], c['area'], c['lat'], c['lon'], g_map, g_sat, mapple, c['reason']
        ])
        
    conn.commit()
    conn.close()
    
    # CSV出力
    header = ["ID", "エリア", "緯度", "経度", "Googleマップ", "航空写真", "Mappleリンク", "選定理由"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(output_data)
        
    return csv_path

if __name__ == "__main__":
    path = generate_serious_10()
    print(f"CEO飯田: 厳選10地点を生成しDBに登録しました: {path}")
