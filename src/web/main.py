import sqlite3
import random
import time
import os
import stripe
import bcrypt
import requests as http_requests
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
import gc
import geopandas as gpd
import pyarrow.parquet as pq_meta
from pathlib import Path

app = FastAPI(title="EneMap AI API")

# 動的探索エンジンのインスタンス
dynamic_finder = DynamicFinder()

# 境界値のみキャッシュ（GeoDataFrame は都度読み捨て、メモリ節約）
_FUDE_BOUNDS_CACHE: dict = {}   # filename → (minx, miny, maxx, maxy)
_AGRI_BOUNDS_CACHE: dict = {}
PROCESSED_DIR = Path("data/processed")

def _get_bounds_from_metadata(pq_file):
    """GeoParquet メタデータから bbox を読む（フルロード不要・数ミリ秒）"""
    try:
        meta = pq_meta.read_metadata(str(pq_file))
        if b'geo' in meta.metadata:
            geo = json.loads(meta.metadata[b'geo'])
            col = geo.get('primary_column', 'geometry')
            bbox = geo.get('columns', {}).get(col, {}).get('bbox')
            if bbox and len(bbox) == 4:
                return tuple(bbox)
    except Exception:
        pass
    return None

_FUDE_COLS = ['polygon_uuid', 'land_type', 'geometry']

def _load_gdf(pq_file, bbox=None, columns=None):
    """
    bbox=(west,south,east,north): repartition_parquet.py 実行後に有効（行グループフィルタ）
    columns: 不要列スキップでメモリ削減（即時有効）
    """
    kwargs = {}
    if columns:
        kwargs['columns'] = columns
    if bbox:
        try:
            gdf = gpd.read_parquet(pq_file, bbox=bbox, **kwargs)
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(epsg=4326)
            return gdf
        except (ValueError, Exception):
            pass  # bbox未対応ファイルはフルロードにフォールバック
    gdf = gpd.read_parquet(pq_file, **kwargs)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf

def _get_bounds(pq_file, cache):
    key = pq_file.name
    if key not in cache:
        bounds = _get_bounds_from_metadata(pq_file)
        if bounds is None:
            gdf = _load_gdf(pq_file)
            bounds = tuple(gdf.total_bounds)
            del gdf
        cache[key] = bounds
    return cache[key]

# --- 設定 (環境変数から取得) ---
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = STRIPE_API_KEY

DB_PATH = os.getenv("DB_PATH", "data/green_battery.db")

# 起動時にDBを初期化
@app.on_event("startup")
def startup_event():
    print(f"CEO飯田: データベースを初期化しています ({DB_PATH})...")
    init_product_db(DB_PATH)
    # INITIAL_ALLOWED_EMAILS=email1:note1,email2:note2 で招待メールをプリロード
    initial_emails = os.getenv("INITIAL_ALLOWED_EMAILS", "")
    if initial_emails:
        conn = get_db_connection()
        for entry in initial_emails.split(","):
            parts = entry.strip().split(":", 1)
            email = parts[0].strip()
            note = parts[1].strip() if len(parts) > 1 else ""
            if email:
                conn.execute("INSERT OR IGNORE INTO allowed_emails (email, note) VALUES (?, ?)", (email, note))
        conn.commit()
        conn.close()
        print(f"招待メール登録完了: {initial_emails}")
    # INITIAL_USERS=email:password,email2:password2 で初期ユーザーをプリロード
    initial_users = os.getenv("INITIAL_USERS", "")
    print(f"INITIAL_USERS env: '{initial_users}'")
    if initial_users:
        try:
            conn = get_db_connection()
            for entry in initial_users.split(","):
                parts = entry.strip().split(":", 1)
                print(f"  entry='{entry}' parts={parts}")
                if len(parts) == 2:
                    email, password = parts[0].strip(), parts[1].strip()
                    if email and password:
                        salt = bcrypt.gensalt()
                        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
                        conn.execute("INSERT OR IGNORE INTO allowed_emails (email, note) VALUES (?, ?)", (email, "初期テストユーザー"))
                        existing = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
                        if not existing:
                            conn.execute("INSERT INTO users (email, hashed_password) VALUES (?, ?)", (email, hashed))
                            print(f"初期ユーザー作成: {email}")
                        else:
                            print(f"初期ユーザー既存: {email}")
            conn.commit()
            conn.close()
            print("INITIAL_USERS 処理完了")
        except Exception as e:
            print(f"INITIAL_USERS エラー: {e}")
    # ADMIN_EMAILS=email1,email2 で管理者フラグをセット
    admin_emails = os.getenv("ADMIN_EMAILS", "")
    if admin_emails:
        conn = get_db_connection()
        for email in [e.strip() for e in admin_emails.split(",") if e.strip()]:
            conn.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        print(f"管理者フラグ設定完了: {admin_emails}")

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

def _log_action(email: str, action: str, details: str, ip: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO action_logs (user_email, action, details, ip_address) VALUES (?, ?, ?, ?)",
            (email, action, details, ip)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

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
    return FileResponse("dashboard_ai_v2.html")

@app.get("/slides")
def read_slides():
    return FileResponse("scripts/slides_anshin.html", media_type="text/html")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "initial_allowed_emails": os.getenv("INITIAL_ALLOWED_EMAILS", ""),
        "initial_users": os.getenv("INITIAL_USERS", ""),
    }

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


ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

def _check_admin(secret: str):
    if not ADMIN_SECRET or secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

@app.post("/api/admin/invite")
def add_invite(email: str, note: str = "", x_admin_secret: str = Header(...)):
    _check_admin(x_admin_secret)
    conn = get_db_connection()
    conn.execute("INSERT OR IGNORE INTO allowed_emails (email, note) VALUES (?, ?)", (email, note))
    conn.commit()
    conn.close()
    return {"ok": True, "email": email}

@app.delete("/api/admin/invite/{email}")
def remove_invite(email: str, x_admin_secret: str = Header(...)):
    _check_admin(x_admin_secret)
    conn = get_db_connection()
    conn.execute("DELETE FROM allowed_emails WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return {"ok": True, "email": email}

@app.delete("/api/admin/users/{email}")
def delete_user(email: str, x_admin_secret: str = Header(...)):
    _check_admin(x_admin_secret)
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return {"ok": True, "email": email}

@app.get("/api/admin/invites")
def list_invites(x_admin_secret: str = Header(...)):
    _check_admin(x_admin_secret)
    conn = get_db_connection()
    rows = conn.execute("SELECT email, note, created_at FROM allowed_emails ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/admin/login-history")
def get_login_history(x_admin_secret: str = Header(...), email: str = None, limit: int = 100):
    _check_admin(x_admin_secret)
    conn = get_db_connection()
    if email:
        rows = conn.execute(
            "SELECT email, success, ip_address, logged_at FROM login_history WHERE email = ? ORDER BY logged_at DESC LIMIT ?",
            (email, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT email, success, ip_address, logged_at FROM login_history ORDER BY logged_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/admin/login-history-jwt")
def get_login_history_jwt(email: str = None, limit: int = 100, current_user: dict = Depends(get_current_user)):
    if not current_user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    conn = get_db_connection()
    if email:
        rows = conn.execute(
            "SELECT email, success, ip_address, logged_at FROM login_history WHERE email = ? ORDER BY logged_at DESC LIMIT ?",
            (email, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT email, success, ip_address, logged_at FROM login_history ORDER BY logged_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/auth/token", response_model=Token)
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (form_data.username,)).fetchone()

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        conn.execute(
            "INSERT INTO login_history (email, success, ip_address) VALUES (?, 0, ?)",
            (form_data.username, ip)
        )
        conn.commit()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_token = str(uuid.uuid4())
    conn.execute("UPDATE users SET session_token = ? WHERE email = ?", (session_token, user["email"]))
    conn.execute(
        "INSERT INTO login_history (email, success, ip_address) VALUES (?, 1, ?)",
        (user["email"], ip)
    )
    conn.commit()
    conn.close()

    access_token = create_access_token(data={"sub": user["email"], "sid": session_token})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "is_subscribed": bool(current_user["is_subscribed"]),
        "is_admin": bool(current_user["is_admin"]) if current_user["is_admin"] is not None else False
    }

@app.get("/api/candidates", response_model=List[Candidate])
def get_candidates(
    request: Request,
    north: float = None, south: float = None, east: float = None, west: float = None,
    mode: str = "ai",
    max_slope: float = None,
    agri: str = None,
    chimoku: str = None,
    min_dist_bldg: int = None,
    status_filter: str = None,
    current_user: dict = Depends(get_current_user)
):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    _log_action(current_user["email"], "search_candidates",
                json.dumps({"mode": mode, "max_slope": max_slope, "agri": agri, "chimoku": chimoku}), ip)
    conn = get_db_connection()
    if north is not None and south is not None and east is not None and west is not None:
        # AI探索モード: DynamicFinderでリアルタイム発掘
        if mode == "ai":
            try:
                results = dynamic_finder.run_search_in_bounds(north, south, east, west, num_points=60)
                for res in results:
                    lat, lon = res["lat"], res["lon"]
                    c_id = f"RT-{uuid.uuid4().hex[:6].upper()}"
                    size = 0.0001
                    geom_json = json.dumps({
                        "type": "Polygon",
                        "coordinates": [[[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat]]]
                    })
                    cand_status = "有望" if res["slope"] < 2.5 else "要確認"
                    agri_status = "リアルタイム抽出"
                    conn.execute('''
                        INSERT OR IGNORE INTO candidates
                        (id, lat, lon, slope, dist_bldg, agri_status, geometry, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (c_id, lat, lon, res["slope"], res["dist_bldg"], agri_status, geom_json, cand_status))
                if results:
                    conn.commit()
            except Exception as e:
                print(f"リアルタイム発掘エラー: {e}")

        # 共通: bboxフィルター + セルフ探索追加フィルター
        conditions = ["lat <= ?", "lat >= ?", "lon <= ?", "lon >= ?"]
        params = [north, south, east, west]
        if max_slope is not None:
            conditions.append("slope <= ?")
            params.append(max_slope)
        if agri:
            conditions.append("agri_status = ?")
            params.append(agri)
        if chimoku:
            conditions.append("chimoku = ?")
            params.append(chimoku)
        if min_dist_bldg is not None:
            conditions.append("dist_bldg >= ?")
            params.append(min_dist_bldg)
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        query = f"SELECT * FROM candidates WHERE {' AND '.join(conditions)} LIMIT 500"
        rows = conn.execute(query, params).fetchall()
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

@app.get("/api/reverse-geocode")
def reverse_geocode(lat: float, lon: float, current_user: dict = Depends(get_current_user)):
    # 1st: HeartRails GeoAPI（市区町村・町名まで取得可能）
    try:
        res = http_requests.get(
            f"https://geoapi.heartrails.com/api/json?method=searchByGeoLocation&x={lon}&y={lat}",
            timeout=3
        )
        if res.status_code == 200:
            data = res.json()
            locations = data.get("response", {}).get("location", [])
            if locations:
                loc = locations[0]
                address = f"{loc.get('prefecture','')}{loc.get('city','')}{loc.get('town','')}"
                return {"address": address, "prefecture": loc.get("prefecture"), "city": loc.get("city"), "town": loc.get("town")}
    except Exception:
        pass

    # 2nd fallback: 国土地理院 逆ジオコーディング
    try:
        res = http_requests.get(
            f"https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?lat={lat}&lon={lon}",
            timeout=3
        )
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", {})
            if results:
                return {"address": results.get("lv01Nm", "住所不明"), "detail": results}
    except Exception:
        pass

    return {"address": None}

@app.post("/api/registry")
def fetch_registry(request: Request, parcels: List[ParcelRequest], current_user: dict = Depends(get_current_user)):
    if not current_user["is_subscribed"]:
        raise HTTPException(status_code=403, detail="Subscription required for this feature")
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    _log_action(current_user["email"], "fetch_registry",
                json.dumps({"ids": [p.id for p in parcels]}), ip)

    conn = get_db_connection()
    results = []
    for p in parcels:
        time.sleep(0.5)
        chiban = f"大字ダミー {random.randint(1, 999)}番{random.randint(1, 9)}"
        chimoku = random.choice(["山林", "原野", "雑種地"])
        owner = "山形 太郎" if random.random() > 0.5 else "株式会社グリーンテスト"
        
        conn.execute('''
            UPDATE candidates 
            SET chiban=?, chimoku=?, owner=?
            WHERE id=?
        ''', (chiban, chimoku, owner, p.id))
        
        results.append({"id": p.id, "chiban": chiban, "chimoku": chimoku, "owner": owner})
        
    conn.commit()
    conn.close()
    return results

@app.get("/api/layers/fude")
def get_fude_layer(
    request: Request,
    north: float, south: float, east: float, west: float,
    current_user: dict = Depends(get_current_user)
):
    bbox_area = (east - west) * (north - south)
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    _log_action(current_user["email"], "layer_fude",
                json.dumps({"north": round(north,4), "south": round(south,4), "east": round(east,4), "west": round(west,4)}), ip)
    if bbox_area > 0.5:
        raise HTTPException(status_code=400, detail="bbox too large, zoom in further")

    features = []
    for pq_file in sorted(PROCESSED_DIR.glob("*_white_zones.parquet")):
        minx, miny, maxx, maxy = _get_bounds(pq_file, _FUDE_BOUNDS_CACHE)
        if maxx < west or minx > east or maxy < south or miny > north:
            continue

        gdf = _load_gdf(pq_file, bbox=(west, south, east, north), columns=_FUDE_COLS)
        clipped = gdf.cx[west:east, south:north]
        del gdf
        gc.collect()
        if clipped.empty:
            continue
        for _, row in clipped.iterrows():
            features.append({
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {
                    "uuid": str(row.get("polygon_uuid", "")),
                    "land_type": int(row.get("land_type", 0))
                }
            })
            if len(features) >= 2000:
                break
        del clipped
        gc.collect()
        if len(features) >= 2000:
            break

    return {"type": "FeatureCollection", "features": features}


@app.get("/api/layers/agri_zone")
def get_agri_zone_layer(
    request: Request,
    north: float, south: float, east: float, west: float,
    current_user: dict = Depends(get_current_user)
):
    bbox_area = (east - west) * (north - south)
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    _log_action(current_user["email"], "layer_agri_zone",
                json.dumps({"north": round(north,4), "south": round(south,4), "east": round(east,4), "west": round(west,4)}), ip)
    if bbox_area > 2.0:
        raise HTTPException(status_code=400, detail="bbox too large, zoom in further")

    features = []
    for pq_file in sorted(PROCESSED_DIR.glob("*_agri_zones.parquet")):
        minx, miny, maxx, maxy = _get_bounds(pq_file, _AGRI_BOUNDS_CACHE)
        if maxx < west or minx > east or maxy < south or miny > north:
            continue

        gdf = _load_gdf(pq_file, bbox=(west, south, east, north))
        clipped = gdf.cx[west:east, south:north]
        del gdf
        gc.collect()
        if clipped.empty:
            continue
        for _, row in clipped.iterrows():
            features.append({
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {}
            })
            if len(features) >= 500:
                break
        del clipped
        if len(features) >= 500:
            break

    return {"type": "FeatureCollection", "features": features}


@app.post("/api/stripe/create-checkout-session")
async def create_checkout_session(current_user: dict = Depends(get_current_user)):
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': os.getenv("STRIPE_PRICE_ID", "price_1PXXXXXXXXXXXXX"), 'quantity': 1}],
            mode='subscription',
            success_url=os.getenv("BASE_URL", "http://localhost:8000") + '/?payment=success',
            cancel_url=os.getenv("BASE_URL", "http://localhost:8000") + '/?payment=cancel',
            customer_email=current_user["email"],
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_email')
        if customer_email:
            conn = get_db_connection()
            conn.execute("UPDATE users SET is_subscribed = 1 WHERE email = ?", (customer_email,))
            conn.commit()
            conn.close()
            print(f"💰 サブスクリプション完了: {customer_email}")
    return {"status": "success"}

@app.get("/api/admin/action-logs-jwt")
def get_action_logs_jwt(
    email: str = None, action: str = None, limit: int = 200,
    current_user: dict = Depends(get_current_user)
):
    if not current_user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    conn = get_db_connection()
    conditions, params = [], []
    if email:
        conditions.append("user_email = ?")
        params.append(email)
    if action:
        conditions.append("action = ?")
        params.append(action)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = conn.execute(
        f"SELECT user_email, action, details, ip_address, logged_at FROM action_logs {where} ORDER BY logged_at DESC LIMIT ?",
        params + [limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/admin/users-jwt")
def get_users_jwt(current_user: dict = Depends(get_current_user)):
    if not current_user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT email, is_active, is_subscribed, is_admin, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/admin")
def admin_page():
    return FileResponse("admin_dashboard.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"CEO飯田: SaaS製品版APIサーバー(FastAPI)を起動中 (port={port})...")
    uvicorn.run("src.web.main:app", host="0.0.0.0", port=port, reload=True)
