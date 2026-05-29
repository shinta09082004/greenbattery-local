# --- EneMap AI: データベース／GISデータ取得スクリプト (Windows / PowerShell 版) ---
# download_db.sh の PowerShell 同等版。ローカル(Windows)開発用。
# 使い方: プロジェクトルートで  powershell -ExecutionPolicy Bypass -File scripts\download_db.ps1

$ErrorActionPreference = "Stop"

# プロジェクトルートへ移動（このスクリプトの1つ上の階層）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

New-Item -ItemType Directory -Force -Path "data" | Out-Null

Write-Host "[DB Setup] Google Drive からデータベースをダウンロードします..."

# gdown（Google Drive ダウンローダ）が無ければインストール
python -m pip install -q gdown

# green_battery.db
if (-not (Test-Path "data\green_battery.db")) {
    Write-Host "[DB Setup] green_battery.db をダウンロード中..."
    python -m gdown "1CrK2eBRL6syWVAe7-SdGIO2BsaxIjObH" -O "data\green_battery.db"
    Write-Host "[DB Setup] green_battery.db 完了"
} else {
    Write-Host "[DB Setup] green_battery.db は既に存在します。スキップ。"
}

# project.db
if (-not (Test-Path "data\project.db")) {
    Write-Host "[DB Setup] project.db をダウンロード中..."
    python -m gdown "1TmM_X5_JYBCNkMOCx1-VCjlFh2w1ZZfk" -O "data\project.db"
    Write-Host "[DB Setup] project.db 完了"
} else {
    Write-Host "[DB Setup] project.db は既に存在します。スキップ。"
}

# processed parquet ファイル（農振・筆界GISデータ）
$processedGdriveId = "1FpEsJBf01AZCeJyNE29lLboGECMYj7tX"
$hasProcessed = (Test-Path "data\processed") -and `
    ((Get-ChildItem "data\processed" -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)
if (-not $hasProcessed) {
    Write-Host "[DB Setup] processed データをダウンロード中（初回のみ時間がかかります）..."
    New-Item -ItemType Directory -Force -Path "data\processed" | Out-Null
    python -m gdown --folder "$processedGdriveId" -O "data\processed"
    Write-Host "[DB Setup] processed データ完了"
} else {
    Write-Host "[DB Setup] processed データは既に存在します。スキップ。"
}

Write-Host "[DB Setup] セットアップ完了"
