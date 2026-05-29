import sqlite3
import os

db_path = "data/project.db"
os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 土地情報テーブルの作成
cursor.execute('''
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_name TEXT,
    latitude REAL,
    longitude REAL,
    status TEXT DEFAULT '未確認',
    google_maps_url TEXT,
    mapple_url TEXT,
    owner_info TEXT,
    memo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()
print(f"CEO飯田: ローカルDBを初期化しました: {db_path}")
