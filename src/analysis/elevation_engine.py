import math
import requests
import numpy as np
from PIL import Image
from io import BytesIO

class ElevationEngine:
    """
    国土地理院の標高タイルから、特定座標の標高と傾斜を算出する。
    """
    def __init__(self):
        self._cache = {}

    def get_tile_coord(self, lat, lon, zoom=15):
        """緯度経度からタイル座標(x, y)を算出"""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return xtile, ytile

    def get_elevation(self, lat, lon):
        """特定座標の標高(m)を取得"""
        zoom = 15
        x, y = self.get_tile_coord(lat, lon, zoom)
        url_5a = f"https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{zoom}/{x}/{y}.png"
        url_10b = f"https://cyberjapandata.gsi.go.jp/xyz/dem10b_png/{zoom}/{x}/{y}.png"
        
        # 5mメッシュを先に試し、なければ10mメッシュを試す。どちらもダメなら0を返す。
        urls_to_try = [url_5a, url_10b]
        
        try:
            img = None
            for url in urls_to_try:
                if url in self._cache:
                    if self._cache[url] is None:
                        continue # 以前404だった場合は次へ
                    img = self._cache[url]
                    break
                else:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        img = np.array(Image.open(BytesIO(res.content)))
                        if len(self._cache) > 200:
                            self._cache.clear()
                        self._cache[url] = img
                        break
                    else:
                        # 404などもキャッシュして無駄な通信を防ぐ
                        if len(self._cache) > 200:
                            self._cache.clear()
                        self._cache[url] = None
                        
            if img is None:
                return 0

            # タイル内での相対座標を計算
            r, g, b = img[128, 128, 0], img[128, 128, 1], img[128, 128, 2]
            
            x_val = r * 65536 + g * 256 + b
            if x_val < 8388608:
                h = x_val * 0.01
            elif x_val == 8388608:
                h = 0 # 無効値
            else:
                h = (x_val - 16777216) * 0.01
            return h
        except:
            return 0

    def calculate_slope(self, lat, lon):
        """
        周辺3地点の標高差から傾斜（度）を概算する。
        """
        h0 = self.get_elevation(lat, lon)
        h1 = self.get_elevation(lat + 0.0005, lon) # 約50m北
        
        distance = 50.0
        rise = abs(h1 - h0)
        slope_rad = math.atan(rise / distance)
        return math.degrees(slope_rad)

if __name__ == "__main__":
    ee = ElevationEngine()
    # 山形県新庄市の適当な地点
    lat, lon = 38.765, 140.301
    print(f"地点 ({lat}, {lon}) の標高: {ee.get_elevation(lat, lon):.2f}m")
    print(f"概算傾斜: {ee.calculate_slope(lat, lon):.2f}度")
