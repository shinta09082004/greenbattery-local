import sqlite3
import os
import geopandas as gpd
from src.analysis.elevation_engine import ElevationEngine
from shapely.geometry import Point

def populate_product_db_with_real_data(pref_code="04", pref_name="miyagi"):
    print(f"[{pref_name.upper()}] リアルな解析結果をデータベースに登録中...")
    
    parquet_path = f"data/processed/{pref_code}_{pref_name}_white_zones.parquet"
    if not os.path.exists(parquet_path):
        print(f"エラー: 抽出済みのデータ {parquet_path} が見つかりません。")
        return

    # 1. パルケットのロード
    print("白地データをロード中...")
    white_zones = gpd.read_parquet(parquet_path)
    print(f"白地ポリゴン総数: {len(white_zones):,} 筆")
    print(f"現在のCRS: {white_zones.crs}")
    
    # 日本測地系(JGD2000/JGD2011)等の場合、LeafletやGoogle Mapsで正しく表示するため
    # 確実に世界測地系(WGS84: EPSG=4326)に変換する
    if white_zones.crs != "EPSG:4326":
        print("CRSをEPSG:4326 (WGS84) に変換中...")
        white_zones = white_zones.to_crs("EPSG:4326")

    # 実機デモ用: ランダムに2000件サンプリング (すぐ終わるようにする)
    sample_size = min(2000, len(white_zones))
    print(f"今回はデモ用として、ランダムに {sample_size} 件をサンプリングして傾斜を判定します。")
    sample_zones = white_zones.sample(n=sample_size, random_state=42)

    db_path = "data/green_battery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 以前のデータを消去
    cursor.execute("DELETE FROM candidates")

    ee = ElevationEngine()
    count = 0
    total_checked = 0

    for idx, row in sample_zones.iterrows():
        total_checked += 1
        
        # ポリゴンの代表点（中心点）を取得
        centroid = row.geometry.centroid
        lat, lon = centroid.y, centroid.x
        
        # 標高エンジンで傾斜を計算
        slope = ee.calculate_slope(lat, lon)
        dist = 100 # 民家離隔は現状シミュレーション (本番は建物ポリゴンと演算)
        agri = "白地" 
        
        if slope < 5.0:
            status = "有望" if slope < 2.5 else "要確認"
            c_id = f"{pref_code}-{pref_name[:3].upper()}-{count:04d}"
            
            # ポリゴン形状をGeoJSON文字列に変換
            import json
            from shapely.geometry import mapping
            geom_json = json.dumps(mapping(row.geometry))
            
            cursor.execute('''
                INSERT OR IGNORE INTO candidates (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (c_id, lat, lon, round(slope, 1), dist, agri, geom_json, status))
            count += 1
            
        if total_checked % 500 == 0:
            print(f"  {total_checked} 件チェック完了... (合格: {count} 件)")

    conn.commit()
    conn.close()
    print(f"データベースの登録が完了しました！ リアルお宝用地: {count} 件")

if __name__ == "__main__":
    populate_product_db_with_real_data("04", "miyagi")
