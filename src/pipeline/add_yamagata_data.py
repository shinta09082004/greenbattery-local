import sqlite3
import os
import random
import json
import geopandas as gpd
from shapely.geometry import mapping
from src.analysis.elevation_engine import ElevationEngine

def add_yamagata_data():
    print("山形県のデータをデータベースに追記中...")
    parquet_path = "data/processed/06_yamagata_white_zones.parquet"
    if not os.path.exists(parquet_path):
        print("エラー: 山形県のデータが見つかりません。")
        return

    white_zones = gpd.read_parquet(parquet_path)
    if white_zones.crs != "EPSG:4326":
        white_zones = white_zones.to_crs("EPSG:4326")

    sample_size = min(2000, len(white_zones))
    print(f"今回はデモ用として、ランダムに {sample_size} 件をサンプリングして傾斜を判定します。")
    sample_zones = white_zones.sample(n=sample_size, random_state=42)

    db_path = "data/green_battery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    ee = ElevationEngine()
    count = 0
    total = len(sample_zones)

    for idx, row in sample_zones.iterrows():
        centroid = row.geometry.centroid
        lat, lon = centroid.y, centroid.x
        
        slope = ee.calculate_slope(lat, lon)
        dist = 100 
        agri = "白地" 
        
        if slope < 5.0:
            status = "有望" if slope < 2.5 else "要確認"
            c_id = f"06-YAM-{count:04d}"
            geom_json = json.dumps(mapping(row.geometry))
            
            cursor.execute('''
                INSERT OR IGNORE INTO candidates (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (c_id, lat, lon, round(slope, 1), dist, agri, geom_json, status))
            count += 1
            
        if count % 100 == 0 and count > 0:
            print(f"  {count} 件合格...")

    conn.commit()
    conn.close()
    print(f"山形県のデータ登録完了！: {count} 件追加されました。")

if __name__ == "__main__":
    add_yamagata_data()
