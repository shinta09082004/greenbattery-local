import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import random
import zipfile

def generate_dummy_gis_data(pref_code="06", pref_name="yamagata"):
    """
    パイプラインをテストするため、本物と同じ形式(Shapefile)のダミーデータを作成しZIP化する。
    新庄市(38.765, 140.301) 周辺にポリゴンを生成。
    """
    os.makedirs("data/gis_raw/temp", exist_ok=True)
    base_lat, base_lon = 38.765, 140.301

    print("1. ダミー筆ポリゴン(数千件)を生成中...")
    fude_polygons = []
    # 30x30 = 900件の農地ポリゴンを生成
    for i in range(30):
        for j in range(30):
            # 約10m四方の小さな四角形
            lat = base_lat + (i * 0.0002)
            lon = base_lon + (j * 0.0002)
            poly = Polygon([
                (lon, lat),
                (lon + 0.0001, lat),
                (lon + 0.0001, lat + 0.0001),
                (lon, lat + 0.0001)
            ])
            fude_polygons.append(poly)
            
    fude_gdf = gpd.GeoDataFrame(
        {"id": [f"F-{i}" for i in range(len(fude_polygons))]},
        geometry=fude_polygons,
        crs="EPSG:4326"
    )
    # Shapefileとして保存し、ZIP化
    fude_dir = "data/gis_raw/temp/fude"
    os.makedirs(fude_dir, exist_ok=True)
    fude_gdf.to_file(f"{fude_dir}/fude.shp")
    
    with zipfile.ZipFile(f"data/gis_raw/{pref_code}_{pref_name}_fude.zip", 'w') as zf:
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            if os.path.exists(f"{fude_dir}/fude{ext}"):
                zf.write(f"{fude_dir}/fude{ext}", f"fude{ext}")

    print("2. ダミー農業振興地域(青地)を生成中...")
    # 全体の約半分を覆う「青地」の大きなポリゴンを生成
    agri_poly = Polygon([
        (base_lon, base_lat),
        (base_lon + 0.006, base_lat),
        (base_lon + 0.006, base_lat + 0.003),
        (base_lon, base_lat + 0.003)
    ])
    agri_gdf = gpd.GeoDataFrame({"zone": ["青地"]}, geometry=[agri_poly], crs="EPSG:4326")
    
    agri_dir = "data/gis_raw/temp/agri"
    os.makedirs(agri_dir, exist_ok=True)
    agri_gdf.to_file(f"{agri_dir}/agri.shp")

    with zipfile.ZipFile(f"data/gis_raw/{pref_code}_{pref_name}_agri_zone.zip", 'w') as zf:
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            if os.path.exists(f"{agri_dir}/agri{ext}"):
                zf.write(f"{agri_dir}/agri{ext}", f"agri{ext}")

    print("ダミーデータの生成とZIP化が完了しました。")

if __name__ == "__main__":
    generate_dummy_gis_data("06", "yamagata")
