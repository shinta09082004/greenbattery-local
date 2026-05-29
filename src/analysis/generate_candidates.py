import csv
import random

def generate_candidates():
    # ターゲットエリアの中心座標と範囲
    areas = [
        {"name": "新庄市", "lat": 38.762, "lon": 140.301, "count": 40},
        {"name": "大蔵村", "lat": 38.618, "lon": 140.155, "count": 30},
        {"name": "真室川町", "lat": 38.852, "lon": 140.258, "count": 30}
    ]
    
    candidates = []
    id_counter = 1
    
    for area in areas:
        for _ in range(area["count"]):
            # 中心から約2km程度の範囲でランダムに生成
            lat = area["lat"] + (random.random() - 0.5) * 0.04
            lon = area["lon"] + (random.random() - 0.5) * 0.04
            
            # リンク生成
            g_map = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            g_sat = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}&basemap=satellite"
            mapple = f"https://labs.mapple.com/mapplexml.html#18/{lat}/{lon}"
            
            candidates.append([
                id_counter, area["name"], lat, lon, g_map, g_sat, mapple
            ])
            id_counter += 1
            
    # CSV書き出し
    header = ["ID", "エリア", "緯度", "経度", "Googleマップ", "航空写真", "Mappleリンク"]
    file_path = "data/processed/candidates/top_100_candidates.csv"
    
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(candidates)
    
    return file_path

if __name__ == "__main__":
    path = generate_candidates()
    print(f"CEO飯田: 100件の候補地リストを生成しました: {path}")
