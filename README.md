# EneMap AI 土地発掘システム

「EneMap AI」は、日本全国の数千万筆に及ぶ農地データから、系統用蓄電池の設置に最適な「お宝用地」を高速に抽出・管理するためのSaaS型プラットフォームです。

## 主な機能
1. **全国対応の超高速UI**: 47都道府県・全市町村の住所から瞬時に地図を移動し、Googleハイブリッド航空写真上で候補地を俯瞰できます。
2. **空間演算バッチ処理**: 数GBのGISデータ（筆ポリゴン・農業振興地域）をPyOGRIOで高速に結合し、「平坦・接道・非青地」の条件を満たす土地だけを事前抽出します。
3. **登記情報の一括取得API**: 選択した候補地の地番・地目・所有者情報をバックエンドサーバー経由で取得し、SQLiteデータベースに永続化します。

## システムアーキテクチャ
- **Frontend**: HTML5, Vanilla JS, Leaflet.js, Google Maps Hybrid Tiles
- **Backend API**: Python (FastAPI, Uvicorn)
- **Database**: SQLite3 (`data/green_battery.db`)
- **Data Pipeline**: GeoPandas, PyOGRIO, Shapely, PyArrow

## セットアップと起動手順

ローカル（Windows / macOS）でも GitHub Codespaces でも同じ手順で動作します。
**全コマンドはプロジェクトルート（`greenbattery-local`）で実行してください。**

### 0. （任意）仮想環境の作成

<details>
<summary>Windows (PowerShell)</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
</details>

<details>
<summary>macOS / Linux / Codespaces (bash)</summary>

```bash
python -m venv .venv
source .venv/bin/activate
```
</details>

### 1. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 環境変数の設定（任意）
`.env.template` を `.env` にコピーして値を編集します。未設定でもコード側のデフォルト値で動作します。

- Windows (PowerShell): `Copy-Item .env.template .env`
- macOS / Linux: `cp .env.template .env`

### 3. データベース／GISデータの取得
Google Drive から本番DBとGISデータを取得します（既に存在する場合はスキップ）。

- Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File scripts\download_db.ps1`
- macOS / Linux / Codespaces: `bash scripts/download_db.sh`

> データを取得せずに空のDBで起動したい場合は `python src/utils/init_product_db.py` で初期化できます。

### 4. サーバーの起動
FastAPIサーバーは必ず `uvicorn` モジュール経由で、プロジェクトルートから起動します
（`src` パッケージを import するため。`python src/web/main.py` 直接実行は import エラーになります）。

```bash
python -m uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload
```
起動後、ブラウザで `http://localhost:8000` にアクセスしてください。
（Codespaces では VS Code がポート8000を自動フォワードします。）

## 開発者向け
- データのスクレイピングが必要な場合は `src/crawler/gis_downloader.py` を使用します。
- タイルからの標高・傾斜計算エンジンは `src/analysis/elevation_engine.py` に実装されています。
