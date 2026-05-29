import sqlite3
import os
import random
import geopandas as gpd
from src.analysis.elevation_engine import ElevationEngine
from src.pipeline.load_to_db import populate_product_db

def add_real_miyagi_data():
    print("宮城県のリアルデータ（特に仙台市周辺）をデータベースに追記中...")
    
    parquet_path = "data/processed/04_miyagi_white_zones.parquet"
    if not os.path.exists(parquet_path):
        print("エラー: 宮城県のデータが見つかりません。")
        return

    # 白地データをロード
    white_zones = gpd.read_parquet(parquet_path)
    if white_zones.crs != "EPSG:4326":
        white_zones = white_zones.to_crs("EPSG:4326")

    # 仙台市周辺（緯度38.2～38.35, 経度140.7～141.0）の白地農地を抽出
    # cx[minx:maxx, miny:maxy]
    sendai_zones = white_zones.cx[140.7:141.0, 38.2:38.35]
    
    # 仙台市周辺から100件、宮城県全体から100件をサンプリング
    sample_sendai = sendai_zones.sample(n=min(100, len(sendai_zones)), random_state=42)
    sample_miyagi = white_zones.sample(n=min(100, len(white_zones)), random_state=42)
    
    import pandas as pd
    combined_zones = pd.concat([sample_sendai, sample_miyagi])

    db_path = "data/green_battery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    ee = ElevationEngine()
    count = 0
    total = len(combined_zones)
    current = 0

    for idx, row in combined_zones.iterrows():
        current += 1
        
        centroid = row.geometry.centroid
        lat, lon = centroid.y, centroid.x
        
        # 標高エンジンで傾斜を計算
        slope = ee.calculate_slope(lat, lon)
        dist = random.randint(50, 200) # 民家離隔はシミュレーション
        agri = "白地" 
        
        if slope < 5.0:
            status = "有望" if slope < 2.5 else "要確認"
            c_id = f"04-MIY-{count:04d}"
            
            import json
            from shapely.geometry import mapping
            geom_json = json.dumps(mapping(row.geometry))
            
            cursor.execute('''
                INSERT OR IGNORE INTO candidates (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (c_id, lat, lon, round(slope, 1), dist, agri, geom_json, status))
            count += 1
            
        if current % 50 == 0:
            print(f"  {current}/{total} 件処理中... (合格: {count}件)")

    conn.commit()
    conn.close()
    print(f"宮城県のリアルデータ登録完了！: {count} 件追加されました。")

if __name__ == "__main__":
    # 1. 全国ダミーデータ（山形含む）を登録 (DELETE FROM が実行される)
    populate_product_db()
    # 2. 宮城県のリアルデータを追記
    add_real_miyagi_data()
