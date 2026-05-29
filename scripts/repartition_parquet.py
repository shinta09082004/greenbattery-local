"""
parquet ファイルを空間ソート + 複数 row group で再書き出し。
実行後は gpd.read_parquet(path, bbox=...) が有効になりメモリ使用量が大幅削減。

使い方:
    python scripts/repartition_parquet.py
    python scripts/repartition_parquet.py --dry-run   # サイズ確認のみ
"""
import argparse
import geopandas as gpd
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
ROW_GROUP_SIZE = 30_000  # 行グループあたり行数。小さいほどフィルタ精度↑・ファイルサイズ↑


def repartition(pq_file: Path, dry_run: bool = False):
    print(f"\n{pq_file.name}")
    gdf = gpd.read_parquet(pq_file)
    print(f"  rows: {len(gdf):,}  cols: {list(gdf.columns)}")

    if len(gdf) == 0:
        print("  skip (empty)")
        return

    # 代表点でソート（point_lng/lat があれば使う、なければ重心）
    if "point_lng" in gdf.columns and "point_lat" in gdf.columns:
        gdf = gdf.sort_values(["point_lat", "point_lng"]).reset_index(drop=True)
    else:
        centroids = gdf.geometry.centroid
        gdf = gdf.assign(_lat=centroids.y, _lng=centroids.x)
        gdf = gdf.sort_values(["_lat", "_lng"]).drop(columns=["_lat", "_lng"]).reset_index(drop=True)

    n_groups = max(1, len(gdf) // ROW_GROUP_SIZE)
    print(f"  → {n_groups} row groups (size={ROW_GROUP_SIZE:,})")

    if dry_run:
        return

    # write_covering_bbox=True で bbox フィルタを有効化
    tmp = pq_file.with_suffix(".tmp.parquet")
    gdf.to_parquet(
        tmp,
        row_group_size=ROW_GROUP_SIZE,
        write_covering_bbox=True,
        compression="zstd",
    )
    tmp.replace(pq_file)
    print(f"  done → {pq_file.stat().st_size / 1024**2:.1f} MB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = sorted(PROCESSED_DIR.glob("*.parquet"))
    print(f"対象: {len(files)} ファイル  dry_run={args.dry_run}")

    for f in files:
        try:
            repartition(f, dry_run=args.dry_run)
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n完了")


if __name__ == "__main__":
    main()
