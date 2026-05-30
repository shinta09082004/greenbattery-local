---
name: openenemap
description: EneMap AIアプリを起動してURLを表示する。ユーザーが "openenemap" または "/openenemap" と入力したとき、あるいはEneMapアプリを開きたいときに使う。
user-invocable: true
allowed-tools:
  - Bash
  - PowerShell
---

EneMap AI（FastAPI サーバー）を起動し、アクセスURLを表示する。
**Codespace（Linux）・ローカル（Windows / macOS）のどちらでも動作する。**

## 前提

- カレントディレクトリはプロジェクトルート（`greenbattery-local`）であること。パスは固定せず、常にプロジェクトルートを基準にする。
- サーバーは必ず `python -m uvicorn src.web.main:app` で起動する（プロジェクトルートが sys.path に入り `src` パッケージが import できるため）。`python src/web/main.py` は import エラーになるので使わない。

## 手順

実行環境を判定し、OS に応じたコマンドを使う。

### A. Windows（ローカル / PowerShell）

1. ポート8000の使用状況を確認：
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
```

2. 未起動の場合、バックグラウンドで起動（`PowerShell` ツールの `run_in_background: true` で実行）：
```powershell
python -m uvicorn src.web.main:app --host 0.0.0.0 --port 8000
```

3. 起動確認：
```powershell
(Invoke-WebRequest -Uri http://localhost:8000/ -UseBasicParsing -TimeoutSec 10).StatusCode
```

### B. Codespace / Linux / macOS（Bash）

1. ポート8000の使用状況を確認：
```bash
lsof -i :8000 | grep LISTEN || echo "free"
```

2. 未起動の場合、バックグラウンドで起動：
```bash
python -m uvicorn src.web.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
sleep 3
```

3. 起動確認：
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

## 結果の伝え方

- サーバーが起動済み/起動成功: `http://localhost:8000` をブラウザで開くよう案内する
- 起動失敗:
  - Windows: バックグラウンドタスクの出力（`PowerShell` ツールの背景出力）を確認してエラーを報告
  - Codespace/Linux/macOS: `server.log` の末尾を確認してエラーを報告

## 注意

- すでにサーバーが起動している場合はそのまま使える旨を伝える
- Codespace では VS Code のポートフォワード機能により、ブラウザで `http://localhost:8000` を直接開ける
- 初回はデータベース（`data/green_battery.db`）が必要。無い場合は Windows なら `scripts/download_db.ps1`、Linux/macOS なら `bash scripts/download_db.sh` で取得するよう案内する
