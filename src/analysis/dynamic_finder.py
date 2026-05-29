import random
import geopandas as gpd
import osmnx as ox
import math
from shapely.geometry import Point
from src.analysis.elevation_engine import ElevationEngine
import warnings

# ログ出力を抑制
ox.settings.log_console = False
ox.settings.use_cache = True
warnings.filterwarnings('ignore')

class DynamicFinder:
    def __init__(self):
        self.ee = ElevationEngine()

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000 # 地球の半径 (m)
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2.0)**2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda/2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def run_search_in_bounds(self, north, south, east, west, num_points=60, max_slope=5.0, min_bldg_dist=50.0, max_road_dist=10.0):
        # 1. 探索範囲の中心点と半径を計算
        center_lat = (north + south) / 2.0
        center_lon = (east + west) / 2.0
        
        # 画面の対角線の半分の距離を半径とする（最大で600mに制限。広すぎるとOSMの取得に時間がかかるため）
        radius = self._haversine_distance(center_lat, center_lon, north, east)
        dist = min(int(radius), 600)
        
        print(f"🤖 AI自律スカウト開始: 中心({center_lat:.4f}, {center_lon:.4f}) 半径 {dist}m / {num_points}エージェント / 条件: 傾斜<{max_slope} 建物>{min_bldg_dist}m 道路<{max_road_dist}m")
        
        b_proj = gpd.GeoDataFrame()
        e_proj = gpd.GeoDataFrame()

        # 2. OSMデータの「超高速」一括取得 (グラフ構築を避けて生データだけ取得する)
        try:
            tags = {'building': True, 'highway': ['primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'service', 'track']}
            features = ox.features_from_point((center_lat, center_lon), tags=tags, dist=dist)
            
            if not features.empty:
                features_proj = features.to_crs(epsg=3857)
                if 'building' in features_proj.columns:
                    b_proj = features_proj[features_proj['building'].notna()]
                if 'highway' in features_proj.columns:
                    e_proj = features_proj[features_proj['highway'].notna()]
        except Exception as e:
            print(f"⚠️ OSM取得エラーまたはデータなし: {e}")

        # 3. AI自律探索ロジック
        valid_candidates = []
        
        # 初期エージェントの配置
        agents = []
        for _ in range(num_points):
            lat = south + random.random() * (north - south)
            lon = west + random.random() * (east - west)
            agents.append({"lat": lat, "lon": lon})

        # エージェントを地形と道路に合わせて「移動」させる (AI最適化ステップ)
        for agent in agents:
            # 現在地のポイント（投影済み）
            pt_gdf = gpd.GeoDataFrame(geometry=[Point(agent["lon"], agent["lat"])], crs="EPSG:4326").to_crs(epsg=3857)
            pt_proj = pt_gdf.geometry.iloc[0]

            # --- AI移動ルール1: 道路への吸着 ---
            if not e_proj.empty:
                # 最寄りの道路を見つける
                dist_to_roads = e_proj.geometry.distance(pt_proj)
                nearest_road_idx = dist_to_roads.idxmin()
                nearest_road = e_proj.loc[nearest_road_idx].geometry
                dist_road_current = dist_to_roads.min()
                
                # 道路が近く(100m以内)にあるが、接道条件を満たしていない場合、道路の方へ引き寄せる
                if max_road_dist < dist_road_current < 100.0:
                    # 道路上の最も近い点
                    target_point = nearest_road.interpolate(nearest_road.project(pt_proj))
                    # 道路の方向に少し移動させる (AIの引き寄せ)
                    # 目標とする距離を狙う（条件の半分くらい）
                    target_dist = max_road_dist / 2.0
                    move_ratio = (dist_road_current - target_dist) / dist_road_current
                    new_x = pt_proj.x + (target_point.x - pt_proj.x) * move_ratio
                    new_y = pt_proj.y + (target_point.y - pt_proj.y) * move_ratio
                    pt_proj = Point(new_x, new_y)

            # --- AI移動ルール2: 民家からの反発 ---
            if not b_proj.empty:
                dist_to_bldgs = b_proj.geometry.distance(pt_proj)
                nearest_bldg_idx = dist_to_bldgs.idxmin()
                nearest_bldg = b_proj.loc[nearest_bldg_idx].geometry
                dist_bldg_current = dist_to_bldgs.min()
                
                # 民家に近すぎる場合、反対方向に逃げる
                if dist_bldg_current < min_bldg_dist:
                    # 反発ベクトル
                    repel_ratio = ((min_bldg_dist + 5.0) - dist_bldg_current) / max(dist_bldg_current, 1.0)
                    new_x = pt_proj.x - (nearest_bldg.centroid.x - pt_proj.x) * repel_ratio
                    new_y = pt_proj.y - (nearest_bldg.centroid.y - pt_proj.y) * repel_ratio
                    pt_proj = Point(new_x, new_y)

            # 投影座標を緯度経度に戻す
            final_pt_gdf = gpd.GeoDataFrame(geometry=[pt_proj], crs="EPSG:3857").to_crs(epsg=4326)
            new_lat, new_lon = final_pt_gdf.geometry.iloc[0].y, final_pt_gdf.geometry.iloc[0].x

            # --- 最終判定 (厳格な条件) ---
            slope = self.ee.calculate_slope(new_lat, new_lon)
            if slope >= max_slope: continue
            
            # 再計算 (移動後の位置での正確な距離)
            final_pt_proj = pt_proj
            d_bldg = b_proj.geometry.distance(final_pt_proj).min() if not b_proj.empty else float('inf')
            if d_bldg < min_bldg_dist: continue
            
            d_road = e_proj.geometry.distance(final_pt_proj).min() if not e_proj.empty else float('inf')
            if d_road > max_road_dist: continue
            
            valid_candidates.append({
                "lat": new_lat,
                "lon": new_lon,
                "slope": round(slope, 1),
                "dist_bldg": int(d_bldg),
                "dist_road": round(d_road, 1)
            })

        print(f"✨ AI自律探索完了: {len(valid_candidates)} 件の最適地点を収束・発見")
        return valid_candidates
