"""
農業振興地域 ZIP → parquet 変換スクリプト
実行: python3 scripts/process_agri_zones.py
出力: data/processed/{n}_{pref}_agri_zones.parquet（都道府県ごと）
"""

import zipfile
import tempfile
import shutil
from pathlib import Path

import geopandas as gpd

GIS_RAW_DIR  = Path("data/gis_raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def convert_one(zip_path: Path) -> None:
    prefix = zip_path.stem  # 例: 01_hokkaido_agri_zone
    pref_prefix = prefix.replace("_agri_zone", "")  # 例: 01_hokkaido
    out_path = PROCESSED_DIR / f"{pref_prefix}_agri_zones.parquet"

    if out_path.exists():
        print(f"  スキップ（既存）: {out_path.name}")
        return

    tmp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        # shapefile / geojson を自動検出
        shp_files = list(Path(tmp_dir).rglob("*.shp"))
        geojson_files = list(Path(tmp_dir).rglob("*.geojson")) + list(Path(tmp_dir).rglob("*.json"))

        if shp_files:
            gdf = gpd.read_file(shp_files[0])
        elif geojson_files:
            gdf = gpd.read_file(geojson_files[0])
        else:
            print(f"  警告: ベクタファイルが見つかりません → {zip_path.name}")
            return

        if gdf.empty:
            print(f"  警告: データが空です → {zip_path.name}")
            return

        # CRS を WGS84 (EPSG:4326) に統一
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=6668)  # JGD2011（農振データのデフォルト）
        if gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        # geometry 列のみ残す（プロパティが重いため）
        gdf = gdf[["geometry"]].copy()
        gdf = gdf[gdf.geometry.notna() & gdf.geometry.is_valid]

        gdf.to_parquet(out_path, index=False)
        print(f"  完了: {out_path.name}  ({len(gdf):,} ポリゴン, {out_path.stat().st_size // 1024} KB)")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    zip_files = sorted(GIS_RAW_DIR.glob("*_agri_zone.zip"))
    if not zip_files:
        print(f"ZIPファイルが見つかりません: {GIS_RAW_DIR}/*_agri_zone.zip")
        return

    print(f"対象ファイル数: {len(zip_files)}")
    for zp in zip_files:
        print(f"処理中: {zp.name}")
        try:
            convert_one(zp)
        except Exception as e:
            print(f"  エラー: {zp.name} → {e}")

    done = list(PROCESSED_DIR.glob("*_agri_zones.parquet"))
    print(f"\n完了: {len(done)} ファイルを data/processed/ に保存しました")


if __name__ == "__main__":
    main()
