from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# 允許前端網頁連線
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 【資料庫設定區：建立餐廳專屬帳本】
# ==========================================
DB_FILE = "rewards.db" # 這是我們資料庫檔案的名稱

def init_db():
    """廚房開張時的第一件事：檢查有沒有帳本，沒有就買一本"""
    # 1. 建立連線 (如果檔案不存在，它會自動幫你建立一個 rewards.db)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 2. 在帳本裡畫一個表格，叫做 users
    # 裡面有兩個欄位：username (帳號，設定為主要辨識碼 PRIMARY KEY) 和 points (點數，預設為 0)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    ''')
    conn.commit() # 存檔
    conn.close()  # 把帳本合上

# 程式一啟動，就先執行初始化
init_db()


# ==========================================
# 【API 窗口區：現在需要報上名字才能點餐了】
# ==========================================

@app.get("/points")
def get_points(username: str):
    """查詢特定帳號的點數 (網址會變成 /points?username=某某某)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 去 users 表格裡，尋找這個 username 的 points
    cursor.execute("SELECT points FROM users WHERE username = ?", (username,))
    result = cursor.fetchone() # 抓取第一筆結果
    
    if result is None:
        # 如果帳本裡找不到這個人 (新客人)
        # 就幫他在帳本裡建檔，點數給 0
        cursor.execute("INSERT INTO users (username, points) VALUES (?, 0)", (username,))
        conn.commit()
        points = 0
    else:
        # 如果找到這個人，就把他的點數拿出來
        points = result[0]
        
    conn.close()
    return {"username": username, "points": points}

@app.post("/brush")
def brush_teeth(username: str):
    """幫特定帳號打卡，點數 +1"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. 先查出他現在有幾點
    cursor.execute("SELECT points FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    if result is None:
        # 預防他沒查過點數就直接打卡，一樣先幫他建檔
        cursor.execute("INSERT INTO users (username, points) VALUES (?, 0)", (username,))
        current_points = 0
    else:
        current_points = result[0]
    
    # 2. 點數 +1
    new_points = current_points + 1
    
    # 3. 把新點數更新回帳本裡 (UPDATE)
    cursor.execute("UPDATE users SET points = ? WHERE username = ?", (new_points, username))
    conn.commit()
    conn.close()
    
    return {"message": f"{username} 打卡成功！", "points": new_points}