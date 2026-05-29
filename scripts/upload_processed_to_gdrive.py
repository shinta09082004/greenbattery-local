"""
data/processed/ を Google Drive にアップロードするスクリプト。

【事前準備】
1. https://console.cloud.google.com/ でプロジェクトを作成（既存でも可）
2. "Google Drive API" を有効化
3. 認証情報 → OAuth クライアント ID を作成（種類: デスクトップアプリ）
4. credentials.json をダウンロードし、このリポジトリのルートに配置

【実行方法】
    pip install google-api-python-client google-auth-oauthlib
    python scripts/upload_processed_to_gdrive.py

初回のみブラウザ認証が必要（表示されたURLを開いてコードを貼り付け）。
完了後、フォルダIDが表示されるので download_db.sh に記入する。
"""

import os
import sys
import json
from pathlib import Path

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("必要なライブラリをインストールします...")
    os.system("pip install -q google-api-python-client google-auth-oauthlib")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDS_FILE = Path("credentials.json")
TOKEN_FILE = Path(".gdrive_token.json")
UPLOAD_DIR = Path("data/processed")
FOLDER_NAME = "enemap_processed_data"


def authenticate() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(
                    "\n[エラー] credentials.json が見つかりません。\n"
                    "Google Cloud Console から OAuth クライアント ID（デスクトップアプリ）を\n"
                    "ダウンロードして、リポジトリルートに credentials.json として保存してください。\n"
                    "  https://console.cloud.google.com/apis/credentials\n"
                )
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            # ランダムポートでローカルサーバーを立て、URLを表示する
            # Codespace の場合は VS Code がポートを自動フォワードするのでブラウザで開ける
            print("\n認証URLが生成されます。ブラウザで開いて Google アカウントを認証してください。")
            print("（VS Code の「ポート」タブに新しいポートが表示されたら「ブラウザで開く」をクリック）\n")
            creds = flow.run_local_server(port=0, open_browser=False)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def get_or_create_folder(service, name: str) -> str:
    """指定名のフォルダを検索し、なければ作成してフォルダIDを返す"""
    res = service.files().list(
        q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        spaces="drive",
    ).execute()

    files = res.get("files", [])
    if files:
        folder_id = files[0]["id"]
        print(f"[既存フォルダを使用] {name} (ID: {folder_id})")
        return folder_id

    folder_meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=folder_meta, fields="id").execute()
    folder_id = folder["id"]
    print(f"[フォルダ作成] {name} (ID: {folder_id})")
    return folder_id


def set_public_readable(service, file_id: str):
    """gdown でダウンロードできるよう、ファイル/フォルダを「リンクを知っている人が閲覧可」に設定"""
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()


def file_exists_in_folder(service, folder_id: str, filename: str) -> bool:
    res = service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
        fields="files(id)",
    ).execute()
    return bool(res.get("files"))


def upload_file(service, local_path: Path, folder_id: str) -> str:
    filename = local_path.name
    file_meta = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(str(local_path), resumable=True)
    f = service.files().create(body=file_meta, media_body=media, fields="id").execute()
    return f["id"]


def main():
    if not UPLOAD_DIR.exists():
        print(f"[エラー] {UPLOAD_DIR} が存在しません。")
        sys.exit(1)

    files = sorted(UPLOAD_DIR.glob("*.parquet"))
    if not files:
        print(f"[エラー] {UPLOAD_DIR} に .parquet ファイルが見つかりません。")
        sys.exit(1)

    print(f"アップロード対象: {len(files)} ファイル ({UPLOAD_DIR})")
    total_size = sum(f.stat().st_size for f in files)
    print(f"合計サイズ: {total_size / 1024 / 1024:.1f} MB\n")

    print("Google Drive に認証します...")
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)

    folder_id = get_or_create_folder(service, FOLDER_NAME)
    set_public_readable(service, folder_id)

    uploaded = 0
    skipped = 0
    for i, f in enumerate(files, 1):
        prefix = f"[{i}/{len(files)}]"
        size_mb = f.stat().st_size / 1024 / 1024
        if file_exists_in_folder(service, folder_id, f.name):
            print(f"{prefix} スキップ（既存）: {f.name}")
            skipped += 1
            continue

        print(f"{prefix} アップロード中: {f.name} ({size_mb:.1f} MB)...", end=" ", flush=True)
        file_id = upload_file(service, f, folder_id)
        set_public_readable(service, file_id)
        print("完了")
        uploaded += 1

    print(f"\n===== 完了 =====")
    print(f"アップロード: {uploaded} / スキップ: {skipped}")
    print(f"\n【フォルダID（download_db.sh に記入）】")
    print(f"  {folder_id}")
    print(f"\n確認URL: https://drive.google.com/drive/folders/{folder_id}")

    # download_db.sh への追記コマンドを表示
    print(f"""
【次のステップ】scripts/download_db.sh の末尾に以下を追加してください:

# processed parquet ファイル
PROCESSED_GDRIVE_ID="{folder_id}"
if [ ! -d "data/processed" ] || [ -z "$(ls -A data/processed 2>/dev/null)" ]; then
    echo "[DB Setup] processed データをダウンロード中（初回のみ時間がかかります）..."
    pip install -q gdown
    gdown --folder "$PROCESSED_GDRIVE_ID" -O data/processed/ --remaining-ok
    echo "[DB Setup] processed データ完了"
fi
""")


if __name__ == "__main__":
    main()
