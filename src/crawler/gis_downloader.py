from playwright.sync_api import sync_playwright
import os
import time

def download_gis_data_advanced(pref_code="06", pref_name="yamagata"):
    """
    プランB: 完全自動化クローラー
    農水省や国交省のサイトから、対象県のGISデータを執念でダウンロードする。
    """
    os.makedirs("data/gis_raw", exist_ok=True)
    
    with sync_playwright() as p:
        # ボット検知を回避するため、少し人間らしい設定にする
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"--- [{pref_name.upper()}] GIS生データ完全自動取得を開始 ---")

        # ---------------------------------------------------------
        # 1. 農林水産省 筆ポリゴン (FlatGeobuf)
        # ---------------------------------------------------------
        print("1. 農水省 筆ポリゴン公開ページに潜入中...")
        page.goto("https://www.maff.go.jp/j/tokei/porigon/data.html", wait_until="networkidle")
        time.sleep(2) # JSのレンダリング待ち

        # ページ内の全リンクを取得し、"06" または "yamagata" を含み、".zip" で終わるURLを探す
        all_links = page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
        target_fude_url = None
        for link in all_links:
            if link and ".zip" in link.lower() and (pref_code in link or pref_name in link.lower()):
                target_fude_url = link
                break
        
        if target_fude_url:
            print(f"   -> ターゲットURL発見: {target_fude_url}")
            print("   -> ダウンロード強制発火...")
            with page.expect_download(timeout=60000) as download_info:
                # 直接URLに飛んでダウンロードをトリガー
                page.goto(target_fude_url)
            
            download = download_info.value
            fude_save_path = f"data/gis_raw/{pref_code}_{pref_name}_fude.zip"
            download.save_as(fude_save_path)
            print(f"   ✅ 筆ポリゴン取得成功: {fude_save_path} ({os.path.getsize(fude_save_path)/1024/1024:.1f} MB)")
        else:
            print("   ❌ 筆ポリゴンのターゲットURLが見つかりませんでした。サイト構成が変更された可能性があります。")


        # ---------------------------------------------------------
        # 2. 国土数値情報 農業振興地域データ (青地)
        # ---------------------------------------------------------
        print("\n2. 国土数値情報 農業地域データページに潜入中...")
        # KSJのURLルールは比較的固定されているため、直接狙い撃ちする
        # 例: A05-15_06_GML.zip (A05=農業地域, 15=2015年度, 06=都道府県コード)
        agri_base_url = f"https://nlftp.mlit.go.jp/ksj/gml/data/A05/A05-15/A05-15_{pref_code}_GML.zip"
        
        try:
            print(f"   -> ターゲットURL: {agri_base_url}")
            with page.expect_download(timeout=60000) as download_info:
                page.goto(agri_base_url)
            
            download = download_info.value
            agri_save_path = f"data/gis_raw/{pref_code}_{pref_name}_agri_zone.zip"
            download.save_as(agri_save_path)
            print(f"   ✅ 農業地域データ取得成功: {agri_save_path} ({os.path.getsize(agri_save_path)/1024/1024:.1f} MB)")
        except Exception as e:
            print(f"   ❌ 農業地域データの取得に失敗しました: {e}")

        browser.close()
        print("--- 自動取得プロセス完了 ---")

if __name__ == "__main__":
    download_gis_data_advanced("06", "yamagata")
