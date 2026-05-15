from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os
from datetime import datetime, date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS water_logs (
        username TEXT,
        log_date DATE,
        total_ml INTEGER DEFAULT 0,
        milestone_1000 BOOLEAN DEFAULT FALSE,
        milestone_3000 BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (username, log_date)
    )
''')
    conn = get_conn()
    cursor = conn.cursor()

    # 主要點數表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    ''')

    # 每日任務打卡表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_tasks (
            username TEXT,
            task_id TEXT,
            done_date DATE,
            PRIMARY KEY (username, task_id, done_date)
        )
    ''')

    # 商店兌換紀錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_logs (
            id SERIAL PRIMARY KEY,
            username TEXT,
            item_id TEXT,
            cost INTEGER,
            redeemed_at TIMESTAMP DEFAULT NOW()
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# 任務清單（可以之後再加）
TASKS = {
    "brush":   {"name": "刷牙 🪥",  "points": 1},
    "exercise":{"name": "運動 🏃",  "points": 2},
    "sleep":   {"name": "早睡 🌙",  "points": 1},
}
# 商店清單
SHOP_ITEMS = {
    "snack":   {"name": "零食 🍬",    "cost": 5},
    "shopping":{"name": "買東西 🛍️", "cost": 20},
    "massage": {"name": "馬殺雞 💆", "cost": 30},
}

@app.get("/points")
def get_points(username: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO users (username, points) VALUES (%s, 0)", (username,))
        conn.commit()
        points = 0
    else:
        points = result[0]
    conn.close()
    return {"username": username, "points": points}

@app.get("/water")
def get_water(username: str):
    """查詢今天喝水量"""
    conn = get_conn()
    cursor = conn.cursor()
    today = date.today()
    cursor.execute(
        "SELECT total_ml, milestone_1000, milestone_3000 FROM water_logs WHERE username = %s AND log_date = %s",
        (username, today)
    )
    result = cursor.fetchone()
    conn.close()
    if result is None:
        return {"total_ml": 0, "milestone_1000": False, "milestone_3000": False}
    return {"total_ml": result[0], "milestone_1000": result[1], "milestone_3000": result[2]}

@app.post("/water")
def add_water(username: str, ml: int):
    """新增這次喝水量"""
    if ml <= 0:
        raise HTTPException(status_code=400, detail="請輸入正確的水量")

    conn = get_conn()
    cursor = conn.cursor()
    today = date.today()

    # 查今天紀錄
    cursor.execute(
        "SELECT total_ml, milestone_1000, milestone_3000 FROM water_logs WHERE username = %s AND log_date = %s",
        (username, today)
    )
    result = cursor.fetchone()

    if result is None:
        # 今天第一次喝水，建立紀錄
        cursor.execute(
            "INSERT INTO water_logs (username, log_date, total_ml) VALUES (%s, %s, %s)",
            (username, today, ml)
        )
        old_ml = 0
        m1000 = False
        m3000 = False
    else:
        old_ml, m1000, m3000 = result
        cursor.execute(
            "UPDATE water_logs SET total_ml = total_ml + %s WHERE username = %s AND log_date = %s",
            (ml, username, today)
        )

    new_ml = old_ml + ml
    earned = 0
    messages = []

    # 檢查 1000ml 里程碑
    if not m1000 and new_ml >= 1000:
        earned += 1
        messages.append("+1點 🎉 喝水達1000ml！")
        cursor.execute(
            "UPDATE water_logs SET milestone_1000 = TRUE WHERE username = %s AND log_date = %s",
            (username, today)
        )

    # 檢查 3000ml 里程碑
    if not m3000 and new_ml >= 3000:
        earned += 2
        messages.append("+2點 🏆 達標3000ml！")
        cursor.execute(
            "UPDATE water_logs SET milestone_3000 = TRUE WHERE username = %s AND log_date = %s",
            (username, today)
        )

    # 加點數
    if earned > 0:
        cursor.execute(
            "INSERT INTO users (username, points) VALUES (%s, %s) ON CONFLICT (username) DO UPDATE SET points = users.points + %s",
            (username, earned, earned)
        )

    conn.commit()
    cursor.execute("SELECT points FROM users WHERE username = %s", (username,))
    new_points = cursor.fetchone()[0]
    conn.close()

    return {
        "total_ml": new_ml,
        "earned": earned,
        "message": " ".join(messages) if messages else f"已記錄 {ml}ml 💧",
        "points": new_points,
        "milestone_1000": not m1000 and new_ml >= 1000,
        "milestone_3000": not m3000 and new_ml >= 3000
    }

@app.get("/tasks")
def get_tasks(username: str):
    """回傳今天每個任務是否已完成"""
    conn = get_conn()
    cursor = conn.cursor()
    today = date.today()

    cursor.execute(
        "SELECT task_id FROM daily_tasks WHERE username = %s AND done_date = %s",
        (username, today)
    )
    done_tasks = {row[0] for row in cursor.fetchall()}
    conn.close()

    result = {}
    for task_id, info in TASKS.items():
        result[task_id] = {
            "name": info["name"],
            "points": info["points"],
            "done": task_id in done_tasks
        }
    return result

@app.post("/task/{task_id}")
def complete_task(task_id: str, username: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="任務不存在")

    conn = get_conn()
    cursor = conn.cursor()
    today = date.today()

    # 檢查今天是否已打卡
    cursor.execute(
        "SELECT 1 FROM daily_tasks WHERE username = %s AND task_id = %s AND done_date = %s",
        (username, task_id, today)
    )
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="今天已經完成這個任務了！")

    # 寫入打卡紀錄
    cursor.execute(
        "INSERT INTO daily_tasks (username, task_id, done_date) VALUES (%s, %s, %s)",
        (username, task_id, today)
    )

    # 加點數
    earned = TASKS[task_id]["points"]
    cursor.execute(
        "INSERT INTO users (username, points) VALUES (%s, %s) ON CONFLICT (username) DO UPDATE SET points = users.points + %s",
        (username, earned, earned)
    )

    conn.commit()

    # 回傳最新點數
    cursor.execute("SELECT points FROM users WHERE username = %s", (username,))
    new_points = cursor.fetchone()[0]
    conn.close()

    return {"message": f"{TASKS[task_id]['name']} 完成！+{earned}點", "points": new_points}

@app.post("/shop/{item_id}")
def redeem_item(item_id: str, username: str):
    if item_id not in SHOP_ITEMS:
        raise HTTPException(status_code=404, detail="商品不存在")

    item = SHOP_ITEMS[item_id]
    conn = get_conn()
    cursor = conn.cursor()

    # 檢查點數夠不夠
    cursor.execute("SELECT points FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    if result is None or result[0] < item["cost"]:
        conn.close()
        raise HTTPException(status_code=400, detail="點數不足！")

    # 扣點數
    cursor.execute(
        "UPDATE users SET points = points - %s WHERE username = %s",
        (item["cost"], username)
    )

    # 寫入兌換紀錄
    cursor.execute(
        "INSERT INTO shop_logs (username, item_id, cost) VALUES (%s, %s, %s)",
        (username, item_id, item["cost"])
    )

    conn.commit()
    cursor.execute("SELECT points FROM users WHERE username = %s", (username,))
    new_points = cursor.fetchone()[0]
    conn.close()

    return {"message": f"成功兌換 {item['name']}！", "points": new_points}

@app.get("/shop")
def get_shop():
    return SHOP_ITEMS