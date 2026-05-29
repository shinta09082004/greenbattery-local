import sqlite3
import random
import time
import os
import stripe
import bcrypt
from fastapi import FastAPI, HTTPException, Depends, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
from src.utils.init_product_db import init_product_db
from src.analysis.dynamic_finder import DynamicFinder
import json
import uuid

app = FastAPI(title="EneMap AI Ver.AI API")

# 動的探索エンジンのインスタンス
dynamic_finder = DynamicFinder()

# --- 設定 (環境変数から取得) ---
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = STRIPE_API_KEY

# データベースファイルは共有
DB_PATH = os.getenv("DB_PATH", "data/green_battery.db")

# 起動時にDBを初期化 (テーブルの存在を保証)
@app.on_event("startup")
def startup_event():
    print(f"🤖 Ver.AI: データベースをチェック中 ({DB_PATH})...")
    init_product_db(DB_PATH)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Candidate(BaseModel):
    id: str
    lat: float
    lon: float
    slope: float
    dist: int
    agri: str
    geometry: Optional[str] = None
    status: str
    chiban: Optional[str] = None
    chimoku: Optional[str] = None
    owner: Optional[str] = None

class ParcelRequest(BaseModel):
    id: str
    lat: float
    lon: float

# --- Utilities ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    sid: str = payload.get("sid")

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user is None:
        raise credentials_exception
    if sid != user["session_token"]:
        raise credentials_exception
    return user

# --- Endpoints ---

@app.get("/")
def read_index():
    # Ver.AI専用のHTMLを返す (キャッシュ対策でv2を指定)
    return FileResponse("dashboard_ai_v2.html")

@app.get("/api/health")
def health_check():
    return {"status": "healthy (Ver.AI)", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/auth/register")
def register_user(user: UserCreate):
    conn = get_db_connection()
    allowed = conn.execute("SELECT 1 FROM allowed_emails WHERE email = ?", (user.email,)).fetchone()
    if not allowed:
        conn.close()
        raise HTTPException(status_code=403, detail="このメールアドレスは招待されていません")
    existing_user = conn.execute("SELECT * FROM users WHERE email = ?", (user.email,)).fetchone()
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = get_password_hash(user.password)
    conn.execute("INSERT INTO users (email, hashed_password) VALUES (?, ?)", (user.email, hashed_pwd))
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

@app.post("/api/auth/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (form_data.username,)).fetchone()

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_token = str(uuid.uuid4())
    conn.execute("UPDATE users SET session_token = ? WHERE email = ?", (session_token, user["email"]))
    conn.commit()
    conn.close()

    access_token = create_access_token(data={"sub": user["email"], "sid": session_token})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "is_subscribed": bool(current_user["is_subscribed"])
    }

@app.get("/api/candidates", response_model=List[Candidate])
def get_candidates(
    north: float = None, south: float = None, east: float = None, west: float = None,
    max_slope: float = 5.0, min_bldg_dist: float = 50.0, max_road_dist: float = 10.0, num_points: int = 60,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db_connection()
    if north is not None and south is not None and east is not None and west is not None:
        try:
            # リアルタイム発掘 (Ver.AIでも基本ロジックは共有)
            results = dynamic_finder.run_search_in_bounds(
                north, south, east, west,
                num_points=num_points, max_slope=max_slope, min_bldg_dist=min_bldg_dist, max_road_dist=max_road_dist
            )
            for res in results:
                lat, lon = res["lat"], res["lon"]
                c_id = f"AI-{uuid.uuid4().hex[:6].upper()}"
                # AI結果はポリゴンを持たせない (None)
                geom_json = None
                status = "有望" if res["slope"] < 2.5 else "要確認"
                agri_status = "AIリアルタイム抽出"
                
                conn.execute('''
                    INSERT OR IGNORE INTO candidates 
                    (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (c_id, lat, lon, res["slope"], res["dist_bldg"], agri_status, geom_json, status))
            if results:
                conn.commit()
        except Exception as e:
            print(f"リアルタイム発掘エラー: {e}")

        query = '''
            SELECT * FROM candidates 
            WHERE lat <= ? AND lat >= ? AND lon <= ? AND lon >= ?
            LIMIT 500
        '''
        rows = conn.execute(query, (north, south, east, west)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM candidates ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    
    return [
        Candidate(
            id=r["id"], lat=r["lat"], lon=r["lon"],
            slope=r["slope"], dist=r["dist_bldg"], agri=r["agri_status"],
            geometry=r["geometry"],
            status=r["status"], chiban=r["chiban"], chimoku=r["chimoku"], owner=r["owner"]
        ) for r in rows
    ]

# --- 登記API (Ver.AI) ---
@app.post("/api/registry")
def fetch_registry(parcels: List[ParcelRequest], current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    results = []
    for p in parcels:
        # Ver.AIではシミュレーションでもAIコメントを追加予定
        chiban = f"AI区ダミー {random.randint(1, 999)}番"
        chimoku = random.choice(["原野", "雑種地"])
        owner = "AI未来開発株式会社"
        
        conn.execute('UPDATE candidates SET chiban=?, chimoku=?, owner=? WHERE id=?', (chiban, chimoku, owner, p.id))
        results.append({"id": p.id, "chiban": chiban, "chimoku": chimoku, "owner": owner})
        
    conn.commit()
    conn.close()
    return results

if __name__ == "__main__":
    import uvicorn
    # Ver.AIはポート 8001 で起動
    port = int(os.getenv("PORT", 8001))
    print(f"🤖 CEO飯田: EneMap AI Ver.AI サーバーを起動中 (port={port})...")
    uvicorn.run("src.web.main_ai:app", host="0.0.0.0", port=port, reload=True)
