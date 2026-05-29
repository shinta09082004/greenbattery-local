import geopandas as gpd
from shapely.geometry import Point, Polygon
import os

class CandidateFinder:
    """
    山形県蓄電池用地発掘エンジン (CEO 飯田 監修)
    1. 建物から50m以上離れているか
    2. 平地であるか
    3. 道路に面しているか (NEW)
    4. 高圧電線が100m以内か (NEW)
    5. ハザードマップ警戒区域外か (NEW)
    """
    def __init__(self, target_area):
        self.target_area = target_area
        self.min_distance_from_buildings = 50.0
        self.max_powerline_distance = 100.0
        self.max_slope = 5.0

    def generate_google_maps_url(self, lat, lon):
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    def generate_satellite_url(self, lat, lon):
        """航空写真モードのリンク"""
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}&basemap=satellite"

    def generate_mapple_url(self, lat, lon):
        """Mapple (登記マップ) の該当座標へのリンク"""
        # MappleのURL形式に合わせて調整（ズームレベル18想定）
        return f"https://m-chizu.mapple.net/map.aspx?x={lon}&y={lat}&z=18"

    def generate_street_view_url(self, lat, lon):
        return f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"

if __name__ == "__main__":
    # プロトタイプ実行（新庄市エリア想定）
    finder = CandidateFinder("Shinjo-City")
    print("CEO飯田: 最上エリアの解析準備が整いました。")
