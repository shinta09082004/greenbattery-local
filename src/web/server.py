import http.server
import socketserver
import urllib.parse
import json
import sqlite3
import os
import sys

# 自作モジュールのインポート用
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from web.dashboard_generator import generate_dashboard
from analysis.refill_candidate import refill_candidate

PORT = 8000
DB_PATH = "data/project.db"

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(post_data)

        if self.path == '/update':
            # ステータス更新
            prop_id = data.get('id')
            status = data.get('status')
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE properties SET status = ? WHERE id = ?", (status, prop_id))
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
            
            # ダッシュボードを再生成
            generate_dashboard()

        elif self.path == '/refill':
            # 見送り削除 & 1件補充
            result = refill_candidate()
            generate_dashboard()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "details": result}).encode())

    def do_GET(self):
        if self.path == '/' or self.path == '/dashboard.html':
            # アクセスのたびに最新を生成
            generate_dashboard()
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"CEO飯田: 実戦用ダッシュボードサーバーを起動しました: http://localhost:{PORT}")
        print("判定結果は即座にDBに反映され、補充サイクルが実行可能です。")
        httpd.serve_forever()
