import sqlite3
import random
import os
from src.analysis.elevation_engine import ElevationEngine

def populate_product_db(db_path="data/green_battery.db"):
    print("全国の主要都市を中心にダミー解析結果を製品版データベースに登録中...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 一度クリア
    cursor.execute("DELETE FROM candidates")

    ee = ElevationEngine()
    
    # 全国の主要なテストポイント（緯度、経度、プレフィックス）
    locations = [
        {"name": "新庄市", "lat": 38.765, "lon": 140.301, "prefix": "SNJ"},
        {"name": "山形市", "lat": 38.255, "lon": 140.340, "prefix": "YMG"},
        {"name": "仙台市", "lat": 38.268, "lon": 140.871, "prefix": "SND"},
        {"name": "盛岡市", "lat": 39.702, "lon": 141.154, "prefix": "MRK"},
        {"name": "札幌市", "lat": 43.062, "lon": 141.354, "prefix": "SPR"},
        {"name": "東京都", "lat": 35.689, "lon": 139.691, "prefix": "TKY"},
        {"name": "大阪市", "lat": 34.693, "lon": 135.502, "prefix": "OSK"},
        {"name": "福岡市", "lat": 33.590, "lon": 130.401, "prefix": "FUK"},
        {"name": "那覇市", "lat": 26.212, "lon": 127.681, "prefix": "NHA"}
    ]
    
    count = 0
    for loc in locations:
        base_lat = loc["lat"]
        base_lon = loc["lon"]
        
        # 各エリアに20件程度の候補地をばらまく
        for i in range(20):
            lat = base_lat + (random.random() - 0.5) * 0.05
            lon = base_lon + (random.random() - 0.5) * 0.05
            
            slope = ee.calculate_slope(lat, lon)
            dist = random.randint(50, 200)
            agri = "白地" if random.random() > 0.2 else "青地"
            
            if slope < 5.0 and agri == "白地":
                status = "有望" if slope < 2.5 else "要確認"
                c_id = f"{loc['prefix']}-PRO-{count:04d}"
                
                # ダミーのポリゴン形状（四角形）を生成
                import json
                geom_json = json.dumps({
                    "type": "Polygon",
                    "coordinates": [[
                        [lon, lat], [lon+0.001, lat], [lon+0.001, lat+0.001], [lon, lat+0.001], [lon, lat]
                    ]]
                })
                
                cursor.execute('''
                    INSERT INTO candidates (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (c_id, lat, lon, round(slope, 1), dist, agri, geom_json, status))
                count += 1
                
    conn.commit()
    conn.close()
    print(f"全国データベースの登録が完了しました！ お宝用地: {count} 件")

if __name__ == "__main__":
    populate_product_db()
