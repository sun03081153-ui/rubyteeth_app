from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 從環境變數讀取資料庫網址（安全做法）
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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

@app.post("/brush")
def brush_teeth(username: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO users (username, points) VALUES (%s, 0)", (username,))
        current_points = 0
    else:
        current_points = result[0]
    new_points = current_points + 1
    cursor.execute("UPDATE users SET points = %s WHERE username = %s", (new_points, username))
    conn.commit()
    conn.close()    
    return {"message": f"{username} 真是個超級乖寶寶！", "points": new_points}