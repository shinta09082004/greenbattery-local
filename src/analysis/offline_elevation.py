import math

class OfflineElevationEngine:
    """
    ローカルの標高データ(GeoTIFF等)を使用して、API通信なしで爆速で傾斜を計算するエンジン。
    ※本番環境では rasterio を用いてローカルのDEMファイルを読み込みます。
    今回はデモとして、座標のハッシュ値を用いた擬似的な(しかし超高速な)計算を行います。
    """
    def __init__(self, dem_path="data/dem_local/japan_dem_mock.tif"):
        self.dem_path = dem_path
        self.is_ready = True

    def calculate_slope(self, lat, lon):
        """
        API通信を行わず、メモリ上で瞬時に傾斜を算出する。
        （デモ用擬似ロジック: 緯度経度の小数点以下の値から0〜15度の傾斜を決定）
        """
        # 実際の運用ではここで rasterio.sample([lon, lat]) を実行して標高を取得する
        # 高速化のため、擬似的に地形の起伏をシミュレート
        val = (math.sin(lat * 1000) + math.cos(lon * 1000)) * 5 + 5
        # 0 〜 10度程度の値になるように調整
        return max(0.0, min(15.0, val))

if __name__ == "__main__":
    ee = OfflineElevationEngine()
    print(f"テスト地点の傾斜: {ee.calculate_slope(38.765, 140.301):.2f} 度")
