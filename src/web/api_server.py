from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import time
import random

app = FastAPI(title="Green Battery API", description="全国版土地探索バックエンドAPI")

# CORS設定（ダッシュボードからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ParcelRequest(BaseModel):
    id: str
    lat: float
    lon: float

class RegistryResponse(BaseModel):
    id: str
    chiban: str # 地番
    chimoku: str # 地目
    owner: str # 所有者(ダミー)
    status: str

@app.get("/")
def read_root():
    return {"message": "Green Battery API is running."}

@app.post("/api/get_registry", response_model=List[RegistryResponse])
def get_registry_info(parcels: List[ParcelRequest]):
    """
    指定された座標リストの登記情報（地番・地目・所有者）を取得する。
    ※本番環境ではここで外部サービス(Mapple/登記情報提供サービス)にスクレイピング/API通信を行う。
    """
    print(f"--- 登記取得リクエストを受信: {len(parcels)}件 ---")
    results = []
    
    for parcel in parcels:
        # 実務では1件あたり数百円かかるため、APIを叩く前にここで厳密なチェックを行う
        print(f"-> {parcel.id} ({parcel.lat}, {parcel.lon}) の登記を照会中...")
        
        # ※外部API通信のシミュレーション（意図的な遅延）
        time.sleep(0.5) 
        
        # Mappleや登記ネットから取得したと仮定したダミーデータ
        results.append(RegistryResponse(
            id=parcel.id,
            chiban=f"大字ダミー字テスト {random.randint(1, 999)}番{random.randint(1, 9)}",
            chimoku=random.choice(["山林", "原野", "雑種地", "畑"]),
            owner="山形 太郎" if random.random() > 0.5 else "株式会社グリーンテスト",
            status="success"
        ))

    print("--- 登記取得完了 ---")
    return results

if __name__ == "__main__":
    import uvicorn
    # 本番運用を想定し、uvicornで起動
    print("CEO飯田: 全国展開用バックエンドAPIを起動します (Port: 8000)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
