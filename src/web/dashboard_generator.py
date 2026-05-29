import sqlite3
import os

def generate_dashboard():
    db_path = "data/project.db"
    html_path = "dashboard.html"
    
    if not os.path.exists(db_path):
        return "CEO飯田: データベースが見つかりません。先に土地抽出を実行してください。"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, area_name, latitude, longitude, google_maps_url, mapple_url, status, memo FROM properties ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>Green Battery 実戦用ダッシュボード (CEO 飯田)</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; color: #1c1e21; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            header {{ display: flex; justify-content: space-between; align-items: center; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 6px solid #2ecc71; }}
            h1 {{ color: #27ae60; margin: 0; font-size: 1.5em; }}
            .controls {{ display: flex; gap: 15px; align-items: center; }}
            .btn-refill {{ background: #e67e22; color: white; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; border: none; transition: background 0.3s; }}
            .btn-refill:hover {{ background: #d35400; }}
            .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; padding: 25px; transition: transform 0.2s; }}
            .card:hover {{ transform: translateY(-2px); }}
            .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }}
            .area-name {{ font-size: 1.3em; font-weight: bold; color: #2c3e50; }}
            .id-badge {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 6px; font-size: 0.8em; margin-right: 12px; }}
            .status-badge {{ padding: 5px 15px; border-radius: 20px; font-size: 0.85em; font-weight: bold; }}
            .status-未確認 {{ background: #ecf0f1; color: #7f8c8d; }}
            .status-有望 {{ background: #2ecc71; color: white; }}
            .status-見送り {{ background: #95a5a6; color: white; }}
            .memo {{ background: #f8f9fa; border-radius: 8px; padding: 15px; font-size: 0.95em; color: #444; margin-bottom: 20px; line-height: 1.5; border: 1px solid #eef0f2; }}
            .actions {{ display: flex; gap: 12px; flex-wrap: wrap; }}
            .btn {{ padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.9em; cursor: pointer; border: none; display: inline-flex; align-items: center; }}
            .btn-gmap {{ background-color: #4285F4; color: white; }}
            .btn-sat {{ background-color: #34A853; color: white; }}
            .btn-mapple {{ background-color: #EA4335; color: white; }}
            .btn-judge-yes {{ background-color: #27ae60; color: white; }}
            .btn-judge-no {{ background-color: #95a5a6; color: white; }}
            .btn:hover {{ opacity: 0.9; filter: brightness(0.9); }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1>Green Battery 土地管理ダッシュボード</h1>
                    <div style="font-size: 0.85em; color: #7f8c8d; margin-top: 5px;">CEO 飯田 監修 | 実戦運用モード</div>
                </div>
                <div class="controls">
                    <span style="font-weight: bold;">候補: {len(rows)}件</span>
                    <button onclick="refill()" class="btn-refill">見送りを削除して補充</button>
                </div>
            </header>
            <div class="list">
    """
    
    for row in rows:
        prop_id, area, lat, lon, g_map, mapple, status, memo = row
        g_sat = g_map + "&basemap=satellite"
        
        html_content += f"""
                <div class="card" id="prop-{prop_id}">
                    <div class="card-header">
                        <span class="area-name"><span class="id-badge">#{prop_id}</span>{area}</span>
                        <span class="status-badge status-{status}">{status}</span>
                    </div>
                    <div class="memo">
                        <strong>選定理由/メモ:</strong><br>
                        {memo}<br>
                        <small style="color:#999;">座標: {lat}, {lon}</small>
                    </div>
                    <div class="actions">
                        <a href="{g_map}" target="_blank" class="btn btn-gmap">地図</a>
                        <a href="{g_sat}" target="_blank" class="btn btn-sat">航空写真</a>
                        <a href="{mapple}" target="_blank" class="btn btn-mapple">登記簿(Mapple)</a>
                        <div style="flex-grow: 1;"></div>
                        <button onclick="updateStatus({prop_id}, '有望')" class="btn btn-judge-yes">有望</button>
                        <button onclick="updateStatus({prop_id}, '見送り')" class="btn btn-judge-no">見送り</button>
                    </div>
                </div>
        """
        
    html_content += """
            </div>
        </div>
        <script>
            async function updateStatus(id, status) {
                const res = await fetch('/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, status })
                });
                if (res.ok) {
                    location.reload();
                } else {
                    alert('更新に失敗しました');
                }
            }

            async function refill() {
                if (!confirm('見送り地点を削除し、新しい候補を補充しますか？')) return;
                const res = await fetch('/refill', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                if (res.ok) {
                    const data = await res.json();
                    alert(`削除: ${data.details.deleted}件 / 補充完了 (ID: ${data.details.new_id})`);
                    location.reload();
                } else {
                    alert('補充に失敗しました');
                }
            }
        </script>
    </body>
    </html>
    """
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return os.path.abspath(html_path)

if __name__ == "__main__":
    path = generate_dashboard()
    print(f"CEO飯田: ダッシュボードを生成しました。こちらをブラウザで開いてください:\n{path}")
