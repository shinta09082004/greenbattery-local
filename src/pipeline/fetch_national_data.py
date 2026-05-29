import os
import requests
from tqdm import tqdm

class DataFetcher:
    """
    全国のオープンデータを自動取得するクラス。
    """
    def __init__(self, base_dir="data/gis_raw"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def download_file(self, url, filename):
        path = os.path.join(self.base_dir, filename)
        if os.path.exists(path):
            print(f"Skipping {filename}, already exists.")
            return path
        
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(path, "wb") as f, tqdm(
            total=total_size, unit='B', unit_scale=True, desc=filename
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                f.write(data)
                pbar.update(len(data))
        return path

    def fetch_yamagata_package(self):
        """
        山形県セットのダウンロード
        """
        # 1. 筆ポリゴン (2024年度公開版)
        fude_url = "https://www.maff.go.jp/j/tokei/porigon/dataset/06_yamagata.zip"
        self.download_file(fude_url, "06_yamagata_fude.zip")

        # 2. 農業地域データ (国土数値情報 - 山形県)
        # ※実際のURLはKSJの仕様に従う
        agri_url = "https://nlftp.mlit.go.jp/ksj/gml/data/A05/A05-15/A05-15_06_GML.zip"
        self.download_file(agri_url, "06_yamagata_agri_zone.zip")
        
        print("山形県の基本データセットの取得が完了しました。")

if __name__ == "__main__":
    fetcher = DataFetcher()
    fetcher.fetch_yamagata_package()
