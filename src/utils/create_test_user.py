import sqlite3
import bcrypt

DB_PATH = "data/green_battery.db"

def create_admin_user():
    email = "admin@example.com"
    password = "password123"
    
    # bcryptを直接使用してハッシュ化
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 既存のadminユーザーを削除して再作成
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    cursor.execute(
        "INSERT INTO users (email, hashed_password, is_subscribed) VALUES (?, ?, ?)",
        (email, hashed_password, 0) # 未課金状態で作成
    )
    
    conn.commit()
    conn.close()
    print(f"✅ テストユーザー作成完了: {email}")

if __name__ == "__main__":
    create_admin_user()
