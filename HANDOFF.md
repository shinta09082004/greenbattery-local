# 作業引継ぎ（2026-05-21）

## リポジトリ
https://github.com/shinta09082004/greenbattery  
ブランチ: ローカル `master` → リモート `main`（push時: `git push origin master:main`）

---

## 背景
GitHubへのpushがファイル容量超過で失敗していた。  
原因: `.gitignore` が空で GISデータ(5.1GB)・キャッシュ(1.6GB)・DBがgit管理されており `.git` が6GBに膨張。

---

## 完了した作業

### リポジトリクリーンアップ ✅
- `.gitignore` を作成（除外: `data/gis_raw/`, `data/processed/`, `cache/`, `*.db`, `__pycache__` 等）
- `.git` を削除・`git init` でリセット（6GB → 2.9MB）
- クリーンな状態でpush済み

### Codespaces環境構築 ✅
- `.devcontainer/devcontainer.json` — Codespace起動時に自動でpip install + DB取得
- `scripts/download_db.sh` — DBのみ取得（2.3MB、Webサーバーテスト用）
- `scripts/download_all_data.sh` — 全データ取得（約6GB、パイプライン含むフル環境）

---

## データ管理（Google Drive）

| ファイル | ファイルID |
|---------|-----------|
| `green_battery.db` (2.2MB) | `1CrK2eBRL6syWVAe7-SdGIO2BsaxIjObH` |
| `project.db` (68KB) | `1TmM_X5_JYBCNkMOCx1-VCjlFh2w1ZZfk` |
| `data/gis_raw/` フォルダ (5.1GB) | `1wfRUSP1csKTJUa9eW75vZ7DyL81uWa6I` |
| `data/processed/` フォルダ (489MB) | `1cWOI2oKY-BSvmh_O6dYae6DB_xltR3Kw` |

---

## Codespace起動後の手順

```bash
# Webサーバーテストのみ（DBは自動取得済み）
python src/web/main.py

# パイプラインも使いたい場合（約6GB・時間かかる）
bash scripts/download_all_data.sh
python src/pipeline/run_japan_batch.py
```

---

## 重要な技術的事実
- **Webサーバーは `green_battery.db` のみ参照**（gis_raw・processedはパイプライン専用）
- Codespace容量: 約11GB使用 / 32GB（Proプラン無料枠内、追加課金なし）
- 標高データはWebサーバー実行時に国土地理院APIをHTTPで取得（ローカルファイル不要）

---

## 次にやること
- [ ] Codespace起動して動作確認
- [ ] `bash scripts/download_all_data.sh` でフルデータDLテスト
- [ ] Webサーバー起動・API動作確認
- [ ] パイプライン（`src/pipeline/run_japan_batch.py`）動作確認
