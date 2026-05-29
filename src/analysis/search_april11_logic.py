import os
import csv
import random
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
import osmnx as ox
import math
from src.analysis.elevation_engine import ElevationEngine
from src.analysis.candidate_finder import CandidateFinder

# ログの出力を抑制
ox.settings.log_console = False
ox.settings.use_cache = True

class April11Finder:
    def __init__(self, area_name="山形県新庄市周辺", pref_code="06", pref_name="yamagata", base_lat=38.765, base_lon=140.301):
        self.area_name = area_name
        self.base_lat = base_lat
        self.base_lon = base_lon
        self.ee = ElevationEngine()
        self.finder = CandidateFinder(area_name)
        
        # 1. 農地データのロード (青地・白地の両方を除外するため、fudeを使用)
        self.fude_gdf = self._load_fude_data(pref_code, pref_name)
        
        # 2. OSMデータのロード (指定エリア周辺の建物と道路)
        print(f"[{area_name}] 周辺の建物(民家)と道路データをOSMから取得中...")
        # 中心点から半径約3kmのデータを取得 (少し広めにとる)
        center_point = (base_lat, base_lon)
        dist = 3000
        
        try:
            # 建物データ (tags={'building': True})
            self.buildings = ox.features_from_point(center_point, tags={'building': True}, dist=dist)
            # EPSG:4326 から 平面直角座標系等(距離計算用)へ変換すると正確だが、今回は簡易的にEPSG:4326上で距離を計算するか、投影変換する
            # より正確な距離計算のために投影変換 (Webメルカトル 3857等)
            if not self.buildings.empty:
                 self.buildings_proj = self.buildings.to_crs(epsg=3857)
            else:
                 self.buildings_proj = gpd.GeoDataFrame()
                 
            # 道路データ (network_type='drive') 車が通れる道
            self.graph = ox.graph_from_point(center_point, dist=dist, network_type='drive')
            self.nodes, self.edges = ox.graph_to_gdfs(self.graph)
            if not self.edges.empty:
                self.edges_proj = self.edges.to_crs(epsg=3857)
            else:
                self.edges_proj = gpd.GeoDataFrame()
                
            print(f"取得完了: 建物 {len(self.buildings)}件, 道路 {len(self.edges)}件")
            
        except Exception as e:
            print(f"OSMデータ取得エラー: {e}")
            self.buildings_proj = gpd.GeoDataFrame()
            self.edges_proj = gpd.GeoDataFrame()

    def _load_fude_data(self, pref_code, pref_name):
        print(f"[{self.area_name}] 農地データをロード中...")
        fude_path = f"data/gis_raw/temp/fude/fude.shp" # 以前生成したダミーまたは本物
        # 実際の運用ではZIPを展開したものを読み込むか、ZIPから直接読む
        # ここではダミー生成スクリプトで作ったパスを想定。なければ空のGDFを返す
        if os.path.exists(fude_path):
             gdf = gpd.read_file(fude_path)
             if gdf.crs != "EPSG:4326":
                 gdf = gdf.to_crs("EPSG:4326")
             return gdf
        else:
             print("警告: 農地データ(fude.shp)が見つかりません。農地除外スキップ。")
             return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    def check_distance_to_buildings(self, point_proj):
        """指定したポイント(投影済)から最も近い建物までの距離(m)を計算"""
        if self.buildings_proj.empty:
            return float('inf')
        # 一番近い建物までの距離
        distances = self.buildings_proj.geometry.distance(point_proj)
        return distances.min()

    def check_distance_to_roads(self, point_proj):
        """指定したポイント(投影済)から最も近い道路までの距離(m)を計算"""
        if self.edges_proj.empty:
            return float('inf')
        distances = self.edges_proj.geometry.distance(point_proj)
        return distances.min()

    def run_search(self, num_points=1000):
        print(f"\n--- 探索開始 (対象: {num_points}地点) ---")
        valid_candidates = []
        id_counter = 1
        
        # 探索範囲 (半径約2.5km)
        lat_range = 0.02
        lon_range = 0.025
        
        checked = 0
        passed_slope = 0
        passed_agri = 0
        passed_bldg = 0
        passed_road = 0

        for _ in range(num_points):
            checked += 1
            if checked % 200 == 0:
                print(f"進捗: {checked}/{num_points} ...")
                
            lat = self.base_lat + (random.random() - 0.5) * lat_range * 2
            lon = self.base_lon + (random.random() - 0.5) * lon_range * 2
            point = Point(lon, lat)
            
            # 1. 傾斜判定 (5度以下)
            slope = self.ee.calculate_slope(lat, lon)
            if slope >= 5.0:
                continue
            passed_slope += 1
            
            # 2. 農地判定 (農地ポリゴン内にあれば除外)
            # 速度優先のため、containsで判定
            if not self.fude_gdf.empty:
                # 該当ポイントを含むポリゴンがあるか
                is_agri = self.fude_gdf.geometry.contains(point).any()
                if is_agri:
                    continue
            passed_agri += 1

            # 3 & 4: 距離計算のための投影変換 (EPSG:4326 -> EPSG:3857)
            # GeoPandasを使って変換
            pt_gdf = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326")
            pt_proj = pt_gdf.to_crs(epsg=3857).geometry.iloc[0]

            # 3. 建物からの距離 (50m以上離れていること)
            dist_bldg = self.check_distance_to_buildings(pt_proj)
            if dist_bldg < 50.0:
                continue
            passed_bldg += 1

            # 4. 道路からの距離 (10m以内、路肩吸着)
            dist_road = self.check_distance_to_roads(pt_proj)
            if dist_road > 10.0:
                continue
            passed_road += 1
            
            # --- 全条件クリア ---
            g_map = self.finder.generate_google_maps_url(lat, lon)
            g_sat = self.finder.generate_satellite_url(lat, lon)
            mapple = self.finder.generate_mapple_url(lat, lon)
            street_view = self.finder.generate_street_view_url(lat, lon)
            
            valid_candidates.append([
                f"APR11-{id_counter:03d}",
                self.area_name,
                round(lat, 5),
                round(lon, 5),
                round(slope, 1),
                round(dist_bldg, 1),
                round(dist_road, 1),
                g_map,
                g_sat,
                mapple,
                street_view
            ])
            id_counter += 1

        print("\n--- 探索結果 ---")
        print(f"総チェック数: {checked}")
        print(f"平地クリア: {passed_slope}")
        print(f"非農地クリア: {passed_agri}")
        print(f"民家離隔(50m+)クリア: {passed_bldg}")
        print(f"接道(10m以内)クリア: {passed_road}")
        print(f"🔥 最終お宝用地: {len(valid_candidates)} 件")

        if len(valid_candidates) > 0:
            os.makedirs("data/processed", exist_ok=True)
            csv_path = "data/processed/april11_auto_candidates.csv"
            header = ["ID", "エリア", "緯度", "経度", "傾斜(度)", "建物距離(m)", "道路距離(m)", "Googleマップ", "航空写真", "Mapple", "ストリートビュー"]
            
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(valid_candidates)
            print(f"\n結果を保存しました: {csv_path}")
            return csv_path
        else:
            print("条件を満たす候補地は見つかりませんでした。")
            return None

if __name__ == "__main__":
    # 山形県新庄市周辺をターゲットに探索を実行
    finder = April11Finder(area_name="山形県新庄市周辺", pref_code="06", pref_name="yamagata", base_lat=38.765, base_lon=140.301)
    # テストのため 1000 地点をスキャン
    finder.run_search(num_points=1000)
