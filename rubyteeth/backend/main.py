from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 允許前端網頁連線到這個後端 (CORS 設定)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 暫存點數的變數
current_points = 0

@app.get("/points")
def get_points():
    """取得目前點數"""
    return {"points": current_points}

@app.post("/brush")
def brush_teeth():
    """刷牙打卡，點數 +1"""
    global current_points
    current_points += 1
    return {"message": "打卡成功！", "points": current_points}