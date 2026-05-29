import os
import csv
import random
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import osmnx as ox
import time
from src.analysis.elevation_engine import ElevationEngine
from src.analysis.candidate_finder import CandidateFinder

# ログの出力を抑制
ox.settings.log_console = False
ox.settings.use_cache = True

# 47都道府県の代表的な座標 (県庁所在地または中心地付近)
# 全国を網羅するためのリスト
PREFECTURES = [
    {"code": "01", "name": "hokkaido", "lat": 43.062, "lon": 141.354},
    {"code": "02", "name": "aomori", "lat": 40.824, "lon": 140.740},
    {"code": "03", "name": "iwate", "lat": 39.703, "lon": 141.152},
    {"code": "04", "name": "miyagi", "lat": 38.268, "lon": 140.871},
    {"code": "05", "name": "akita", "lat": 39.718, "lon": 140.102},
    {"code": "06", "name": "yamagata", "lat": 38.240, "lon": 140.363},
    {"code": "07", "name": "fukushima", "lat": 37.750, "lon": 140.467},
    {"code": "08", "name": "ibaraki", "lat": 36.341, "lon": 140.446},
    {"code": "09", "name": "tochigi", "lat": 36.565, "lon": 139.883},
    {"code": "10", "name": "gunma", "lat": 36.391, "lon": 139.060},
    {"code": "11", "name": "saitama", "lat": 35.856, "lon": 139.648},
    {"code": "12", "name": "chiba", "lat": 35.604, "lon": 140.123},
    {"code": "13", "name": "tokyo", "lat": 35.689, "lon": 139.691},
    {"code": "14", "name": "kanagawa", "lat": 35.447, "lon": 139.642},
    {"code": "15", "name": "niigata", "lat": 37.902, "lon": 139.023},
    {"code": "16", "name": "toyama", "lat": 36.695, "lon": 137.211},
    {"code": "17", "name": "ishikawa", "lat": 36.594, "lon": 136.625},
    {"code": "18", "name": "fukui", "lat": 36.064, "lon": 136.221},
    {"code": "19", "name": "yamanashi", "lat": 35.663, "lon": 138.568},
    {"code": "20", "name": "nagano", "lat": 36.651, "lon": 138.181},
    {"code": "21", "name": "gifu", "lat": 35.423, "lon": 136.760},
    {"code": "22", "name": "shizuoka", "lat": 34.976, "lon": 138.383},
    {"code": "23", "name": "aichi", "lat": 35.180, "lon": 136.906},
    {"code": "24", "name": "mie", "lat": 34.730, "lon": 136.508},
    {"code": "25", "name": "shiga", "lat": 35.004, "lon": 135.868},
    {"code": "26", "name": "kyoto", "lat": 35.011, "lon": 135.768},
    {"code": "27", "name": "osaka", "lat": 34.693, "lon": 135.502},
    {"code": "28", "name": "hyogo", "lat": 34.691, "lon": 135.183},
    {"code": "29", "name": "nara", "lat": 34.685, "lon": 135.804},
    {"code": "30", "name": "wakayama", "lat": 34.226, "lon": 135.167},
    {"code": "31", "name": "tottori", "lat": 35.501, "lon": 134.235},
    {"code": "32", "name": "shimane", "lat": 35.472, "lon": 133.050},
    {"code": "33", "name": "okayama", "lat": 34.661, "lon": 133.934},
    {"code": "34", "name": "hiroshima", "lat": 34.385, "lon": 132.455},
    {"code": "35", "name": "yamaguchi", "lat": 34.185, "lon": 131.471},
    {"code": "36", "name": "tokushima", "lat": 34.065, "lon": 134.559},
    {"code": "37", "name": "kagawa", "lat": 34.340, "lon": 134.043},
    {"code": "38", "name": "ehime", "lat": 33.841, "lon": 132.766},
    {"code": "39", "name": "kochi", "lat": 33.559, "lon": 133.531},
    {"code": "40", "name": "fukuoka", "lat": 33.590, "lon": 130.401},
    {"code": "41", "name": "saga", "lat": 33.263, "lon": 130.298},
    {"code": "42", "name": "nagasaki", "lat": 32.750, "lon": 129.877},
    {"code": "43", "name": "kumamoto", "lat": 32.803, "lon": 130.707},
    {"code": "44", "name": "oita", "lat": 33.238, "lon": 131.612},
    {"code": "45", "name": "miyazaki", "lat": 31.907, "lon": 131.420},
    {"code": "46", "name": "kagoshima", "lat": 31.596, "lon": 130.557},
    {"code": "47", "name": "okinawa", "lat": 26.212, "lon": 127.681},
]

class NationalApril11Finder:
    def __init__(self):
        self.ee = ElevationEngine()
        
    def _load_fude_data(self, pref_code, pref_name):
        fude_path = f"data/gis_raw/temp/fude/fude.shp" 
        # 本番では各県のZIPや処理済みParquetを参照する
        if os.path.exists(fude_path):
             gdf = gpd.read_file(fude_path)
             if gdf.crs != "EPSG:4326":
                 gdf = gdf.to_crs("EPSG:4326")
             return gdf
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    def run_national_search(self, points_per_pref=1000):
        print("=" * 50)
        print("🚀 [OSM版] 全国お宝用地発掘バッチを起動します 🚀")
        print("=" * 50)
        
        all_candidates = []
        id_counter = 1
        
        # 探索範囲 (半径約5km)
        lat_range = 0.04
        lon_range = 0.05
        
        for pref in PREFECTURES:
            name_jp = pref['name'].upper()
            print(f"\n--- 📍 {name_jp} ({pref['code']}) の処理を開始 ---")
            
            fude_gdf = self._load_fude_data(pref['code'], pref['name'])
            center_point = (pref['lat'], pref['lon'])
            dist = 5000 # 5km
            
            try:
                print("  OSMデータ(建物/道路)を取得中...")
                buildings = ox.features_from_point(center_point, tags={'building': True}, dist=dist)
                b_proj = buildings.to_crs(epsg=3857) if not buildings.empty else gpd.GeoDataFrame()
                     
                graph = ox.graph_from_point(center_point, dist=dist, network_type='drive')
                nodes, edges = ox.graph_to_gdfs(graph)
                e_proj = edges.to_crs(epsg=3857) if not edges.empty else gpd.GeoDataFrame()
                
            except Exception as e:
                print(f"  ⚠️ OSM取得スキップ (データなし): {e}")
                continue

            checked, passed = 0, 0
            finder = CandidateFinder(name_jp)
            
            print(f"  {points_per_pref} 地点のスキャンを開始...")
            for _ in range(points_per_pref):
                checked += 1
                lat = pref['lat'] + (random.random() - 0.5) * lat_range * 2
                lon = pref['lon'] + (random.random() - 0.5) * lon_range * 2
                point = Point(lon, lat)
                
                slope = self.ee.calculate_slope(lat, lon)
                if slope >= 5.0: continue
                
                if not fude_gdf.empty and fude_gdf.geometry.contains(point).any():
                    continue
                    
                pt_gdf = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326")
                pt_proj = pt_gdf.to_crs(epsg=3857).geometry.iloc[0]
                
                dist_bldg = b_proj.geometry.distance(pt_proj).min() if not b_proj.empty else float('inf')
                if dist_bldg < 50.0: continue
                
                dist_road = e_proj.geometry.distance(pt_proj).min() if not e_proj.empty else float('inf')
                if dist_road > 10.0: continue
                
                # 全条件クリア
                passed += 1
                all_candidates.append([
                    f"NAT-{id_counter:05d}", name_jp, round(lat, 5), round(lon, 5),
                    round(slope, 1), round(dist_bldg, 1), round(dist_road, 1),
                    finder.generate_google_maps_url(lat, lon),
                    finder.generate_satellite_url(lat, lon),
                    finder.generate_mapple_url(lat, lon),
                    finder.generate_street_view_url(lat, lon)
                ])
                id_counter += 1
                
            print(f"  ✅ {name_jp} 完了: {passed} 件抽出")
            time.sleep(1) # OSMサーバーへの配慮

        print("\n" + "=" * 50)
        print(f"🎉 全国スキャン完了！ 🎉")
        print(f"発掘された全国のお宝用地: 合計 {len(all_candidates):,} 件")
        print("=" * 50)

        if all_candidates:
            os.makedirs("data/processed", exist_ok=True)
            csv_path = "data/processed/national_auto_candidates.csv"
            header = ["ID", "都道府県", "緯度", "経度", "傾斜(度)", "建物距離(m)", "道路距離(m)", "Googleマップ", "航空写真", "Mapple", "ストリートビュー"]
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(all_candidates)
            print(f"結果を保存しました: {csv_path}")

if __name__ == "__main__":
    app = NationalApril11Finder()
    # デモ用: 各県ごとに100件ずつスキャン (計4700地点)
    # 本番実行時は 1000 や 5000 などに増やす
    app.run_national_search(points_per_pref=100)
