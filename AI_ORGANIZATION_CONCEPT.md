# EneMap AI — プロジェクト概要・AI組織構造

> 蓄電池設置適地を自動発掘するSaaS型GIS解析プラットフォーム

---

## プロジェクト概要

**EneMap AI**（旧称: Green Battery）は、日本全国の農地・傾斜・農業振興地域データを横断的に解析し、蓄電池設置に適した候補地を自動抽出する SaaS サービスです。

---

## システムアーキテクチャ

```
                    ┌────────────────────────────────────────┐
                    │              ブラウザ                    │
                    │       dashboard_ai_v2.html              │
                    │  Leaflet.js + バニラ HTML/CSS/JS        │
                    │         （シングルファイル）              │
                    └──────────────┬─────────────────────────┘
                                   │ HTTP / JWT Bearer Token
                    ┌──────────────▼─────────────────────────┐
                    │         FastAPI (Uvicorn)               │
                    │         src/web/main.py                 │
                    │                                        │
                    │  /api/auth/*          JWT認証           │
                    │  /api/candidates      候補地検索         │
                    │  /api/layers/agri_zone 農振GeoJSON      │
                    │  /api/layers/fude      白地農地GeoJSON   │
                    │  /api/reverse-geocode  逆ジオコーディング │
                    │  /api/registry         登記情報（モック） │
                    │  /api/stripe/*         Stripe決済       │
                    └──────┬──────────────────┬──────────────┘
                           │                  │
          ┌────────────────▼───┐   ┌──────────▼────────────────┐
          │ SQLite             │   │ GeoParquet（geopandas）    │
          │ data/              │   │ data/processed/            │
          │ green_battery.db   │   │ *_agri_zones.parquet       │
          │ ユーザー・セッション │   │ *_white_zones.parquet      │
          └────────────────────┘   └───────────────────────────┘
```

---

## 技術スタック

| 層 | 技術 | 備考 |
|---|---|---|
| **フロントエンド** | バニラ HTML + Leaflet.js | `dashboard_ai_v2.html` シングルファイル |
| **バックエンド** | Python / FastAPI / Uvicorn | `src/web/main.py` |
| **DB** | SQLite | `data/green_battery.db` |
| **GIS解析** | geopandas / shapely / GeoParquet | 筆ポリゴン・農振データ（47都道府県） |
| **認証** | JWT (python-jose) + bcrypt | session_token でDB側無効化可能 |
| **決済** | Stripe API | サブスクリプション管理 |
| **デプロイ** | Railway (Docker) | 再デプロイでDB初期化、GISデータはDrive経由永続化 |

---

## 主要ファイル構成

```
greenbattery-local/
├── dashboard_ai_v2.html         # フロントエンド全体（分割しない）
├── src/web/main.py              # FastAPI エントリポイント・全API
├── scripts/                     # GISデータ前処理（geopandas）
├── data/
│   ├── green_battery.db         # SQLite DB
│   ├── gis_raw/                 # 都道府県別ZIPファイル（~5.1GB）
│   └── processed/               # 前処理済みparquet
├── CLAUDE.md                    # AI開発ガイドライン（必読）
├── AI_CONTEXT_SPEC/
│   ├── Overview.md              # プロジェクト全体概要
│   ├── Rules.md                 # コーディングルール
│   └── Parallel_Task_Template.md  # 並行作業テンプレート
└── .claude/agents/              # 専門エージェント定義
```

---

## AI組織構造

人間の指示を起点に、**tech-lead** がタスクを分解して専門エージェントへ割り振ります。
フロントエンド＋バックエンドにまたがるタスクは Git worktree を使って並行実行されます。

```
      【人間（プロダクトオーナー）】
                   │ タスク指示
                   ▼
      ┌────────────────────────┐
      │       tech-lead        │  タスク分解・調整（実装しない）
      └──────────┬─────────────┘
                 │
     ┌───────────┼───────────┬──────────────┐
     ▼           ▼           ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
│frontend │ │backend  │ │  gis-   │ │qa-tester │
│  -dev   │ │  -dev   │ │engineer │ │          │
│         │ │         │ │         │ │テスト作成│
│dashboard│ │main.py  │ │scripts/ │ │・実行    │
│_ai_v2   │ │FastAPI  │ │parquet  │ │          │
│Leaflet  │ │SQLite   │ │geopandas│ │          │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘
     ▼           ▼           ▼           │
┌─────────┐ ┌─────────┐ ┌─────────┐     │
│worktree │ │worktree │ │worktree │     │
│    A    │ │    B    │ │    C    │     │
└────┬────┘ └────┬────┘ └────┬────┘     │
     └───────────┼───────────┘          │
                 ▼                      │
      ┌──────────────────┐              │
      │  code-reviewer   │◄─────────────┘
      │  レビュー        │
      └────────┬─────────┘
               ▼
      【マージ → main ブランチ】
      （最終承認は人間が行う）
```

### エージェント一覧

| エージェント | 役割 | 担当ファイル |
|---|---|---|
| `tech-lead` | タスク分解・割り振り | 実装しない |
| `frontend-dev` | UI・Leaflet.js実装 | `dashboard_ai_v2.html` |
| `backend-dev` | API・DB・認証実装 | `src/web/main.py` |
| `gis-engineer` | GISパイプライン | `scripts/*.py` |
| `code-reviewer` | コードレビュー | 実装しない |
| `qa-tester` | テスト作成・実行 | — |
| `product-strategist` | 要件定義・仕様確認 | 実装しない |
| `ux-critic` | UI/UX品質チェック | 実装しない |
| `context-keeper` | ドキュメント・Obsidian更新 | `AI_CONTEXT_SPEC/` |

---

## 重要な設計上の制約

| 制約 | 理由 |
|---|---|
| `dashboard_ai_v2.html` はシングルファイル | Railway での配信・管理を単純化 |
| `/api/layers/fude` は bbox_area ≤ 0.5 sq deg | parquet全件ロードによるOOMクラッシュ防止 |
| `/api/layers/agri_zone` は bbox_area ≤ 20 sq deg | 同上 |
| ズームアウト時はfetch禁止（`_lastFetchZoom`パターン） | フロントエンド側のOOM対策 |
| `git push` / Railway デプロイは人間が承認 | 本番環境の安全確保 |
| `.env` / Secret のハードコード禁止 | セキュリティ |

---

## 開発フロー

```
1. 人間がタスクを指示
        ↓
2. 複数ファイルにまたがる場合 → tech-lead がタスク分解
        ↓
3. 各エージェントが worktree で並行作業
        ↓
4. code-reviewer がレビュー
        ↓
5. 人間が確認 → マージ承認
        ↓
6. 技術変更があれば Google Drive の技術スタック概要を更新
```

> 詳細なルールは `CLAUDE.md` および `AI_CONTEXT_SPEC/Rules.md` を参照。
