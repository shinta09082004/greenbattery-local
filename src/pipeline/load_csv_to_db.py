import sqlite3
import csv
import os
import json

def load_csv_to_db(csv_path="data/processed/national_auto_candidates.csv", db_path="data/green_battery.db"):
    if not os.path.exists(csv_path):
        print(f"エラー: CSVファイル ({csv_path}) が見つかりません。先に抽出スクリプトを実行してください。")
        return

    if not os.path.exists(db_path):
        print(f"エラー: データベース ({db_path}) が存在しません。サーバーを起動してDBを初期化してください。")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"[{csv_path}] からデータを読み込み、ダッシュボード用データベースに登録します...")
    
    count = 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            c_id = row.get("ID")
            lat = float(row.get("緯度", 0))
            lon = float(row.get("経度", 0))
            slope = float(row.get("傾斜(度)", 0))
            dist_bldg = int(float(row.get("建物距離(m)", 0)))
            # 道路距離も取得できるが、DBスキーマにないので現状は無視またはメモに（今回はDB定義に従う）
            
            agri_status = row.get("都道府県", "不明") + " (OSM自動抽出)"
            status = "有望" if slope < 2.5 else "要確認"
            
            # ダッシュボード上でポリゴンを描画するためのダミー矩形 (10m四方)
            size = 0.0001
            geom_json = json.dumps({
                "type": "Polygon",
                "coordinates": [[
                    [lon, lat], 
                    [lon + size, lat], 
                    [lon + size, lat + size], 
                    [lon, lat + size], 
                    [lon, lat]
                ]]
            })

            # すでに存在する場合は上書きしない（あるいはREPLACE INTOを使う）
            cursor.execute('''
                INSERT OR REPLACE INTO candidates 
                (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (c_id, lat, lon, slope, dist_bldg, agri_status, geom_json, status))
            
            count += 1

    conn.commit()
    conn.close()
    
    print(f"✅ 登録完了: {count} 件のお宝用地をダッシュボードに反映しました！")
    print("Webブラウザをリロードして、地図上のピンを確認してください。")

if __name__ == "__main__":
    load_csv_to_db()
