import os
import sqlite3
import geopandas as gpd
import time
from src.pipeline.process_national_data import NationalDataProcessor
from src.analysis.offline_elevation import OfflineElevationEngine

# 47都道府県のコードと英語名マッピング
prefs = {
    "01": "hokkaido", "02": "aomori", "03": "iwate", "04": "miyagi",
    "05": "akita", "06": "yamagata", "07": "fukushima", "08": "ibaraki",
    "09": "tochigi", "10": "gunma", "11": "saitama", "12": "chiba",
    "13": "tokyo", "14": "kanagawa", "15": "niigata", "16": "toyama",
    "17": "ishikawa", "18": "fukui", "19": "yamanashi", "20": "nagano",
    "21": "gifu", "22": "shizuoka", "23": "aichi", "24": "mie",
    "25": "shiga", "26": "kyoto", "27": "osaka", "28": "hyogo",
    "29": "nara", "30": "wakayama", "31": "tottori", "32": "shimane",
    "33": "okayama", "34": "hiroshima", "35": "yamaguchi", "36": "tokushima",
    "37": "kagawa", "38": "ehime", "39": "kochi", "40": "fukuoka",
    "41": "saga", "42": "nagasaki", "43": "kumamoto", "44": "oita",
    "45": "miyazaki", "46": "kagoshima", "47": "okinawa"
}

def run_japan_batch():
    print("=" * 50)
    print("🚀 全国制覇バッチ（全47都道府県処理）を起動します 🚀")
    print("=" * 50)
    
    start_time = time.time()
    
    # 1. データベースの初期化
    db_path = "data/green_battery.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates")
    conn.commit()

    processor = NationalDataProcessor()
    ee = OfflineElevationEngine()
    
    total_candidates = 0

    # 47都道府県をループ
    for code, name in prefs.items():
        raw_fude = f"data/gis_raw/{code}_{name}_fude.zip"
        
        if not os.path.exists(raw_fude):
            print(f"⏭️ スキップ: {name} ({code}) の生データが存在しません。")
            continue
            
        print(f"\n--- 📍 {name.upper()} ({code}) の処理を開始 ---")
        
        # 1. 空間結合（青地除外・白地抽出）
        # ※すでに抽出済みのParquetがあればスキップして高速化
        parquet_path = f"data/processed/{code}_{name}_white_zones.parquet"
        if not os.path.exists(parquet_path):
            success = processor.process_prefecture(code, name)
            if not success:
                continue
                
        # 2. 白地データのロード
        print(f"[{name.upper()}] 白地データをロード中...")
        white_zones = gpd.read_parquet(parquet_path)
        
        # CRS変換
        if white_zones.crs != "EPSG:4326":
            white_zones = white_zones.to_crs("EPSG:4326")
            
        # 本番では全件ですが、デモの速度を優先して各県から最大1000件を抽出
        # （ローカル標高エンジンによりAPI制限はないため本来は全件可能）
        sample_size = min(1000, len(white_zones))
        sample_zones = white_zones.sample(n=sample_size, random_state=42)
        
        print(f"[{name.upper()}] {sample_size} 件のローカル傾斜判定を実行中...")
        
        pref_count = 0
        for idx, row in sample_zones.iterrows():
            centroid = row.geometry.centroid
            lat, lon = centroid.y, centroid.x
            
            # オフラインで一瞬で傾斜を計算
            slope = ee.calculate_slope(lat, lon)
            dist = 100 # 民家離隔
            agri = "白地"
            
            if slope < 5.0:
                status = "有望" if slope < 2.5 else "要確認"
                c_id = f"{code}-{name[:3].upper()}-{pref_count:05d}"
                
                cursor.execute('''
                    INSERT OR IGNORE INTO candidates (id, lat, lon, slope, dist_bldg, agri_status, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (c_id, lat, lon, round(slope, 1), dist, agri, status))
                pref_count += 1
                total_candidates += 1
                
        conn.commit()
        print(f"✅ {name.upper()} 完了: {pref_count} 件のお宝用地をDBに保存しました。")

    conn.close()
    
    elapsed = time.time() - start_time
    print("=" * 50)
    print(f"🎉 全国制覇バッチ完了！ 🎉")
    print(f"総処理時間: {elapsed/60:.1f} 分")
    print(f"発掘された全国のお宝用地: 合計 {total_candidates:,} 件")
    print("=" * 50)

if __name__ == "__main__":
    run_japan_batch()
