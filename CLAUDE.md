# EneMap AI — 開発ガイドライン

## 技術変更時のObsidian連携ワークフロー

### 変更前（必須）

`src/web/main.py` / `dashboard_ai_v2.html` / `scripts/` / 依存ライブラリ に変更を加える前に、
必ず以下の Google Drive ファイルを読み込み、現在の技術スタックと設計方針を確認すること：

- **ツール**: `mcp__claude_ai_Google_Drive__read_file_content`
- **ファイルID**: `1ipQpX4WC3D7Mh_tYlAdCCQvHrzkX2JeQ`
- **内容**: EneMap AI — 技術スタック概要（スタック・API・レイヤー構成・設計上の注意点）

これにより古い実装への後戻りや整合性のない変更を防ぐ。

### 変更後（必須）

技術的な変更（新機能・API追加・レイヤー追加・構成変更）が完了したら、
上記ファイルの内容を最新の状態に更新すること：

- **ツール**: `mcp__claude_ai_Google_Drive__create_file`
- **parentId**: `1MzIYhwDUtb4PYBBBx3_vazCOYnxRd1na`（Green_Battery フォルダ）
- **title**: `EneMap AI — 技術スタック概要`
- **disableConversionToGoogleType**: `true`
- **contentMimeType**: `text/plain`

既存ファイルを更新する場合は古いファイルを削除して新規作成するか、`mcp__claude_ai_Google_Drive__create_file` で同名で上書きする。

### 「技術変更」の定義

以下のファイルへの変更が対象：
- `src/web/main.py` — バックエンド API・認証・DB
- `dashboard_ai_v2.html` — フロントエンド・レイヤー管理
- `scripts/*.py` — データパイプライン
- `requirements.txt` / `Dockerfile` — 依存・デプロイ構成

UIの文言変更・バグ修正のみの場合は更新不要。

## 並行作業ルール

以下のいずれかに該当するタスクを受けた場合は、`Agent` ツールの `isolation: "worktree"` を使って並行サブエージェントを起動する：

- 2ファイル以上にまたがる変更（例：バックエンドAPIとフロントエンドUI両方の修正）
- フロントエンド（`dashboard_ai_v2.html`）とバックエンド（`src/web/main.py`）の両方が変わるタスク
- `tech-lead` エージェントから並行起動の指示があったとき

### 起動手順

1. タスクを分解し、各エージェントへの指示を `AI_CONTEXT_SPEC/Parallel_Task_Template.md` のフォーマットで作成する
2. `Agent` ツールを複数同時呼び出し（`isolation: "worktree"` を必ず指定）
3. 全エージェントの完了後に `code-reviewer` でレビュー
4. 問題なければブランチをマージ

### 担当エージェント対応表

| 変更対象 | 担当エージェント |
|---|---|
| `dashboard_ai_v2.html` / UI / Leaflet.js | `frontend-dev` |
| `src/web/main.py` / FastAPI / SQLite / JWT | `backend-dev` |
| `scripts/*.py` / GeoParquet / geopandas | `gis-engineer` |
| レビュー | `code-reviewer` |
| テスト | `qa-tester` |
| 要件・仕様が曖昧 | `product-strategist` |
| AI_CONTEXT_SPEC / Obsidian 更新 | `context-keeper` |
