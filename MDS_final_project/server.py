import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from or_model import optimize_trip

app = FastAPI()

# 這裡就是擊敗 CORS 魔王的關鍵結界！
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # 這裡填入你 Vite 前端的網址
    allow_credentials=True,
    allow_methods=["*"], # 允許所有方法 (GET, POST 等)
    allow_headers=["*"], # 允許所有標頭
)

# 啟動時預先載入景點資料與車站資料以供名稱對應
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data", "OR_data")
attractions_df = pd.read_csv(os.path.join(data_dir, "attractions.csv"))
station_info_df = pd.read_csv(os.path.join(data_dir, "station_info.csv"))
station_map = dict(zip(station_info_df["station_id"], station_info_df["station_name"]))

def find_attraction_id(name: str) -> str:
    """嘗試根據名稱尋找對應的 attraction_id"""
    # 建立小寫精確匹配
    exact_match = attractions_df[attractions_df['attraction_name'].str.lower() == name.lower()]
    if not exact_match.empty:
        return exact_match.iloc[0]['attraction_id']
    
    # 建立部分匹配
    partial_match = attractions_df[attractions_df['attraction_name'].str.lower().str.contains(name.lower(), na=False)]
    if not partial_match.empty:
        return partial_match.iloc[0]['attraction_id']
    
    return None

@app.post("/api/plan")
async def plan_trip(payload: dict):
    print("收到前端傳來的資料：", payload)
    # 現在 places 是個 list of dict: [{"name": "...", "stay_minutes": 60}, ...]
    places = payload.get("places", [])
    
    attractions = []
    failed_names = []
    
    # 將使用者輸入的名稱轉換為系統可識別的 ID
    for item in places:
        if isinstance(item, str):
            # Backward compatibility check just in case
            n = item
            stay_minutes = 60
        else:
            n = item.get("name", "")
            stay_minutes = item.get("stay_minutes", 60)
            
        if n.startswith("P") and len(n) >= 2 and n[1:].isdigit():
            # 如果使用者直接輸入 P0001 這種格式
            attractions.append({"attraction_id": n, "stay_minutes": stay_minutes, "must_visit": True})
        else:
            aid = find_attraction_id(n)
            if aid:
                attractions.append({"attraction_id": aid, "stay_minutes": stay_minutes, "must_visit": True})
            else:
                failed_names.append(n)
                
    if failed_names and not attractions:
        return {
            "status": "error", 
            "message": f"找不到您輸入的景點：{', '.join(failed_names)}。請嘗試使用更準確的英文名稱（例如：Shibuya Scramble Crossing）。"
        }
            
    # Default fallback if no match found at all
    if not attractions:
        attractions = [
            {"attraction_id": "P0001", "stay_minutes": 90, "must_visit": True},
            {"attraction_id": "P0003", "stay_minutes": 60, "must_visit": True},
            {"attraction_id": "P0008", "stay_minutes": 60, "must_visit": True},
        ]
        
    full_request = {
        "request_id": "api-001",
        "trip_date": "2024-06-15",
        "day_type": "holiday",
        "start_time": "09:00",
        "end_time": "18:00",
        "start_station_id": "G16",  # 為了簡化，預設起終點為同一站，可依前端傳入修改
        "end_station_id": "G16",
        "attractions": attractions,
        "budget_yen": payload.get("budget_yen", 2500),
        "preferences": {
            "time_weight": payload.get("preferences", {}).get("time_weight", 0.5),
            "fare_weight": payload.get("preferences", {}).get("fare_weight", 0.2),
            "crowd_weight": 0.3,
            "avoid_rain": True,
            "rain_penalty_weight": 0.15,
            "max_transfers": 3,
            "include_wait_time": True,
            "allow_skip_attractions": False,
            "prefer_indoor_on_rain": True,
        }
    }
    
    # --- 這裡呼叫你的 OR 模型 ---
    try:
        result = optimize_trip(full_request, data_dir=data_dir)
        
        # 把代碼路線轉換為站名
        if "legs" in result:
            for leg in result["legs"]:
                if "route_path" in leg and leg["route_path"]:
                    path_ids = str(leg["route_path"]).split("→")
                    path_names = [station_map.get(sid, sid) for sid in path_ids]
                    leg["route_path_names"] = path_names

        return result
    except Exception as e:
        print("OR Model Error:", e)
        return {"status": "error", "message": f"模型運算失敗: {str(e)}"}
