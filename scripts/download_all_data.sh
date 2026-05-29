#!/bin/bash
set -e

mkdir -p data/gis_raw data/processed

echo "[Data Setup] Google Drive からデータをダウンロードします..."
echo "[Data Setup] 合計約6GBのダウンロードが始まります。10〜30分かかる場合があります。"

pip install -q "gdown>=5.1.0"

# ── データベース ──────────────────────────────────────────────
echo "[1/4] green_battery.db をダウンロード中..."
gdown "1CrK2eBRL6syWVAe7-SdGIO2BsaxIjObH" -O data/green_battery.db
echo "      完了 (2.2MB)"

echo "[2/4] project.db をダウンロード中..."
gdown "1TmM_X5_JYBCNkMOCx1-VCjlFh2w1ZZfk" -O data/project.db
echo "      完了 (68KB)"

# ── GIS生データ（ZIPフォルダ）────────────────────────────────
# Drive上のフォルダ名が "gis_raw" のため -O data/ で data/gis_raw/ に格納される
GIS_RAW_FOLDER_ID="1cWOI2oKY-BSvmh_O6dYae6DB_xltR3Kw"
echo "[3/4] data/gis_raw/ をダウンロード中 (約5.1GB)..."
gdown --folder "$GIS_RAW_FOLDER_ID" -O data/
echo "      完了"

# ── 処理済みparquet ───────────────────────────────────────────
# Drive上のフォルダ名が "processed" のため -O data/ で data/processed/ に格納される
PROCESSED_FOLDER_ID="1wfRUSP1csKTJUa9eW75vZ7DyL81uWa6I"
echo "[4/4] data/processed/ をダウンロード中 (約489MB)..."
gdown --folder "$PROCESSED_FOLDER_ID" -O data/
echo "      完了"

echo ""
echo "[Data Setup] 全データのセットアップが完了しました"
echo "  data/gis_raw/  : $(find data/gis_raw -type f | wc -l) ファイル"
echo "  data/processed/: $(find data/processed -type f | wc -l) ファイル"
