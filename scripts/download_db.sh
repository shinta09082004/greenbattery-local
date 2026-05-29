#!/bin/bash
set -e

mkdir -p data

echo "[DB Setup] Google Drive からデータベースをダウンロードします..."

pip install -q gdown

# green_battery.db
if [ ! -f "data/green_battery.db" ]; then
    echo "[DB Setup] green_battery.db をダウンロード中..."
    gdown "1CrK2eBRL6syWVAe7-SdGIO2BsaxIjObH" -O data/green_battery.db
    echo "[DB Setup] green_battery.db 完了"
else
    echo "[DB Setup] green_battery.db は既に存在します。スキップ。"
fi

# project.db
if [ ! -f "data/project.db" ]; then
    echo "[DB Setup] project.db をダウンロード中..."
    gdown "1TmM_X5_JYBCNkMOCx1-VCjlFh2w1ZZfk" -O data/project.db
    echo "[DB Setup] project.db 完了"
else
    echo "[DB Setup] project.db は既に存在します。スキップ。"
fi

# processed parquet ファイル（農振・筆界GISデータ）
PROCESSED_GDRIVE_ID="1FpEsJBf01AZCeJyNE29lLboGECMYj7tX"
if [ ! -d "data/processed" ] || [ -z "$(ls -A data/processed 2>/dev/null)" ]; then
    echo "[DB Setup] processed データをダウンロード中（初回のみ時間がかかります）..."
    mkdir -p data/processed
    gdown --folder "$PROCESSED_GDRIVE_ID" -O data/processed
    echo "[DB Setup] processed データ完了"
else
    echo "[DB Setup] processed データは既に存在します。スキップ。"
fi

echo "[DB Setup] セットアップ完了"
