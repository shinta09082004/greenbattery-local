# --- EneMap AI Dockerfile ---
FROM python:3.10-slim

# 1. タイムゾーンの設定 (JST)
ENV TZ=Asia/Tokyo

# 2. システムライブラリのインストール (GIS関連 & ヘルスチェック用)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. GDAL環境変数の設定
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

# 4. 依存ライブラリのコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションコードのコピー
COPY . .

# 6. 環境変数のデフォルト設定
ENV PORT=8000
ENV DB_PATH=/app/data/green_battery.db
ENV PYTHONPATH=/app
ENV SECRET_KEY=super-secret-key-change-me-in-production

# 7. 永続化用ディレクトリの作成
RUN mkdir -p /app/data

# 8. 起動ポートの開放
EXPOSE 8000

# 9. ヘルスチェックの設定
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# 10. startup.sh を実行可能に
RUN chmod +x /app/startup.sh

# 11. 起動コマンド（DBダウンロード → uvicorn 起動）
CMD ["/app/startup.sh"]
