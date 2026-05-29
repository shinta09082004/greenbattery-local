import os
import geopandas as gpd
import pyogrio
import warnings
from shapely.errors import ShapelyDeprecationWarning

# 警告を非表示にしてログをクリーンに保つ
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

class NationalDataProcessor:
    """
    全国規模の巨大なGISデータを高速に処理・結合するためのパイプラインエンジン。
    """
    def __init__(self, raw_dir="data/gis_raw", processed_dir="data/processed"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        os.makedirs(self.processed_dir, exist_ok=True)

    def process_prefecture(self, pref_code="06", pref_name="yamagata"):
        """
        指定した都道府県の「筆ポリゴン」と「青地データ」を空間結合し、
        蓄電池に適した「白地」の農地だけを抽出する。
        """
        print(f"[{pref_name.upper()}] 高速データパイプライン処理を開始します...")

        # ファイルパスの想定 (ダウンロード済みの前提)
        fude_path = os.path.join(self.raw_dir, f"{pref_code}_{pref_name}_fude.zip")
        agri_path = os.path.join(self.raw_dir, f"{pref_code}_{pref_name}_agri_zone.zip")

        # ダミー処理：実際のファイルが存在しない場合はシミュレーションに切り替え
        if not os.path.exists(fude_path) or not os.path.exists(agri_path):
            print(f"⚠️ 警告: {pref_name} の生データが見つかりません。")
            print("  -> ダウンロードが完了するまで、このパイプラインは待機します。")
            print(f"  必要なファイル:\n  - {fude_path}\n  - {agri_path}")
            return False

        try:
            # 1. データの高速読み込み (pyogrioを使用)
            print("1. 筆ポリゴン(数百万件)をロード中...")
            # engine="pyogrio" を指定することで、C言語ベースの超高速読み込みを実現
            fude_gdf = gpd.read_file(fude_path, engine="pyogrio")
            print(f"   -> {len(fude_gdf):,} 筆を読み込みました。")

            print("2. 農業振興地域(青地)ポリゴンをロード中...")
            agri_gdf = gpd.read_file(agri_path, engine="pyogrio")
            print(f"   -> {len(agri_gdf):,} エリアを読み込みました。")

            # 座標参照系 (CRS) の統一 (非常に重要)
            if fude_gdf.crs != agri_gdf.crs:
                print("   -> CRSを統一しています (EPSG:4326/6668)...")
                agri_gdf = agri_gdf.to_crs(fude_gdf.crs)

            # 3. 空間結合 (Spatial Join) による白地抽出
            print("3. 空間演算 (Spatial Join) を実行中... (重い処理です)")
            # 筆ポリゴンの中で、青地ポリゴンと「交差(intersects)しない」ものを残す
            # sjoinは高速だが、メモリを消費するため注意
            
            # 高速化のテクニック：青地ポリゴンを一つの巨大な図形に結合（unary_union）してから判定
            agri_union = agri_gdf.geometry.unary_union
            
            # intersectsの反転(~)で白地を抽出
            white_zone_fude = fude_gdf[~fude_gdf.geometry.intersects(agri_union)]
            
            print(f"   -> 抽出完了: 白地(転用有望)の農地は {len(white_zone_fude):,} 筆です。")

            # 4. 出力 (Parquet形式など、次フェーズで高速に読める形式で保存)
            out_path = os.path.join(self.processed_dir, f"{pref_code}_{pref_name}_white_zones.parquet")
            print(f"4. 抽出結果を保存中: {out_path}")
            # to_parquet は GeoJSON より圧倒的に高速・軽量
            white_zone_fude.to_parquet(out_path)
            
            print(f"[{pref_name.upper()}] パイプライン処理が正常に完了しました！")
            return True

        except Exception as e:
            print(f"❌ 処理中にエラーが発生しました: {e}")
            return False

if __name__ == "__main__":
    processor = NationalDataProcessor()
    processor.process_prefecture("04", "miyagi")
