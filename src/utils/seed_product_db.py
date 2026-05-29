import sqlite3
import os
import json

def seed_product_db(db_path="data/green_battery.db"):
    if not os.path.exists(db_path):
        print(f"エラー: データベース ({db_path}) が存在しません。先にサーバーを起動して初期化してください。")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 既にデータがある場合はスキップ
    cursor.execute("SELECT COUNT(*) FROM candidates")
    if cursor.fetchone()[0] > 0:
        print("既に候補地データが存在します。シード処理をスキップしました。")
        conn.close()
        return

    print("データベースにデモ用のシードデータ（サンプル候補地）を投入しています...")
    
    # サンプルポリゴンの作成 (山形県 新庄市周辺)
    base_lat, base_lon = 38.765, 140.301
    
    def create_rect_polygon(lat, lon, size=0.001):
        return json.dumps({
            "type": "Polygon",
            "coordinates": [[
                [lon, lat], 
                [lon + size, lat], 
                [lon + size, lat + size], 
                [lon, lat + size], 
                [lon, lat]
            ]]
        })

    dummy_data = [
        ("DEMO-YAMAGATA-001", base_lat, base_lon, 1.5, 120, "白地", create_rect_polygon(base_lat, base_lon), "有望", "大字ダミー 123番", "原野", "山形 太郎"),
        ("DEMO-YAMAGATA-002", base_lat + 0.002, base_lon + 0.003, 4.2, 80, "白地", create_rect_polygon(base_lat + 0.002, base_lon + 0.003), "要確認", "大字テスト 45番", "山林", "グリーン法人"),
        ("DEMO-MIYAGI-001", 38.268, 140.871, 2.0, 200, "白地", create_rect_polygon(38.268, 140.871), "有望", "大字仙台 999番", "雑種地", "宮城 幸子")
    ]

    for data in dummy_data:
        cursor.execute('''
            INSERT INTO candidates (id, lat, lon, slope, dist_bldg, agri_status, geometry, status, chiban, chimoku, owner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)

    conn.commit()
    conn.close()
    print("✅ シードデータの投入が完了しました！ダッシュボードを開いて確認できます。")

if __name__ == "__main__":
    # 環境変数から取得（なければデフォルト）
    db_path = os.getenv("DB_PATH", "data/green_battery.db")
    seed_product_db(db_path)
