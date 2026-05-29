import json

class SearchUI:
    """
    全国版土地探索システムの検索画面・管理ロジック。
    """
    def __init__(self):
        # 都道府県・市区町村の階層データ（プロトタイプ用に山形県のみ定義）
        self.regions = {
            "06": {
                "name": "山形県",
                "cities": {
                    "06201": "山形市",
                    "06202": "米沢市",
                    "06203": "鶴岡市",
                    "06204": "酒田市",
                    "06205": "新庄市"
                }
            }
        }
        # 固定パラメーターの選択肢
        self.search_params = {
            "min_distance_from_building": [50, 100, 200],
            "max_slope": [5, 10, 15],
            "agriculture_status": ["白地のみ", "全地目"]
        }

    def render_search_page(self):
        """
        検索画面のHTMLを生成（プロトタイプ用）
        """
        html = f"""
        <html>
        <head><title>Green Battery National Finder</title></head>
        <body>
            <h1>土地探索システム (全国版)</h1>
            <form action="/search" method="get">
                <h3>1. 地域を選択</h3>
                <select name="pref">
                    {"".join([f'<option value="{k}">{v["name"]}</option>' for k,v in self.regions.items()])}
                </select>
                <select name="city">
                    {"".join([f'<option value="{k}">{v}</option>' for k,v in self.regions["06"]["cities"].items()])}
                </select>

                <h3>2. 条件を選択 (爆速検索用プリセット)</h3>
                民家離隔: <select name="dist">
                    {"".join([f'<option value="{v}">{v}m</option>' for v in self.search_params["min_distance_from_building"]])}
                </select>
                最大傾斜: <select name="slope">
                    {"".join([f'<option value="{v}">{v}度</option>' for v in self.search_params["max_slope"]])}
                </select>
                
                <br><br>
                <button type="submit" style="padding:10px 20px; background:#4CAF50; color:white;">お宝用地を検索</button>
            </form>
            
            <hr>
            <div id="results">
                <h3>検索結果 (地図表示予定)</h3>
                <!-- ここに事前計算済みのタイルを表示 -->
                <button onclick="alert('一括登記取得を開始します')">選択中の土地の登記を一括取得</button>
            </div>
        </body>
        </html>
        """
        return html

if __name__ == "__main__":
    ui = SearchUI()
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(ui.render_search_page())
    print("検索画面のプロトタイプ dashboard.html を作成しました。")
