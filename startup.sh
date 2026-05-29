#!/bin/bash

# GISデータ・DBを Google Drive からダウンロード（既に存在する場合はスキップ）
bash /app/scripts/download_db.sh || echo "[startup] download_db.sh でエラーが発生しましたが続行します"

exec uvicorn src.web.main:app --host 0.0.0.0 --port "${PORT:-8000}"
