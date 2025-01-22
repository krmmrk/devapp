# 必要なライブラリのインポート
from fastapi import FastAPI, HTTPException  # FastAPIフレームワークとエラー処理
from fastapi.middleware.cors import CORSMiddleware  # CORS設定用
from fastapi.responses import HTMLResponse  # HTML応答用
from pydantic import BaseModel  # データバリデーション用
from typing import Optional  # 任意フィールド定義用
from datetime import datetime
import sqlite3  # SQLiteデータベース操作用
import uvicorn  # ASGIサーバー

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# CORS（Cross-Origin Resource Sharing）の設定
# フロントエンドからのAPIアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
)

# データベースの初期化関数
def init_db():
    """SQLiteデータベースを初期化し、必要なテーブルを作成する"""
    with sqlite3.connect("meal_records.db") as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自動採番ID
                date_time TIMESTAMP NOT NULL,         -- 食事日時
                meal_type TEXT NOT NULL,              -- 食事の種類（朝食、昼食、夕食、間食）
                food_name TEXT NOT NULL,              -- 食事の名前
                calories INTEGER,                     -- カロリー
                notes TEXT,                          -- メモ
            )
        """
        )

# アプリケーション起動時にデータベースを初期化
init_db()

# 食事データのベースモデル定義
class Meal(BaseModel):
    date_time: datetime  # 食事した日時
    meal_type: str  # 朝食、昼食、夕食、間食など
    food_name: str  # 食事の名前
    calories: Optional[int] = None  # カロリー（省略可能）
    notes: Optional[str] = None  # メモ（省略可能）

# レスポンス用のモデル（IDフィールド追加）
class MealResponse(Meal):
    id: int

# ルートパスへのアクセス時にHTML（クライアントページ）を返す
@app.get("/", response_class=HTMLResponse)
def read_root():
    """クライアント用のHTMLページを返す"""
    with open("client.html", "r", encoding="utf-8") as f:
        return f.read()

# 新しい食事記録を作成するエンドポイント
@app.post("/meals", response_model=MealResponse)
def create_meal(meal: Meal):
    """
    新しい食事記録をデータベースに追加する
    """
    with sqlite3.connect("meal_records.db") as conn:
        cursor = conn.execute(
            """
            INSERT INTO meals 
            (date_time, meal_type, food_name, calories, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (meal.date_time.isoformat(), meal.meal_type, meal.food_name,
             meal.calories, meal.notes),
        )
        meal_id = cursor.lastrowid
        return {**meal.dict(), "id": meal_id}

# すべての食事記録を取得するエンドポイント
@app.get("/meals")
def get_meals():
    """
    すべての食事記録を日時の降順で取得する
    """
    with sqlite3.connect("meal_records.db") as conn:
        meals = conn.execute("SELECT * FROM meals ORDER BY date_time DESC").fetchall()
        return [{
            "id": m[0],
            "date_time": m[1],
            "meal_type": m[2],
            "food_name": m[3],
            "calories": m[4],
            "notes": m[5],
        } for m in meals]

# 特定のIDの食事記録を取得するエンドポイント
@app.get("/meals/{meal_id}")
def get_meal(meal_id: int):
    """
    指定されたIDの食事記録を取得する
    """
    with sqlite3.connect("meal_records.db") as conn:
        meal = conn.execute("SELECT * FROM meals WHERE id = ?", (meal_id,)).fetchone()
        if not meal:
            raise HTTPException(status_code=404, detail="Meal record not found")
        return {
            "id": meal[0],
            "date_time": meal[1],
            "meal_type": meal[2],
            "food_name": meal[3],
            "calories": meal[4],
            "notes": meal[5],
        }

# 特定のIDの食事記録を更新するエンドポイント
@app.put("/meals/{meal_id}")
def update_meal(meal_id: int, meal: Meal):
    """
    指定されたIDの食事記録を更新する
    """
    with sqlite3.connect("meal_records.db") as conn:
        cursor = conn.execute(
            """
            UPDATE meals 
            SET date_time = ?, meal_type = ?, food_name = ?,
                calories = ?, notes = ?, 
            WHERE id = ?
            """,
            (meal.date_time.isoformat(), meal.meal_type, meal.food_name,
             meal.calories, meal.notes, meal_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Meal record not found")
        return {**meal.dict(), "id": meal_id}

# 特定のIDの食事記録を削除するエンドポイント
@app.delete("/meals/{meal_id}")
def delete_meal(meal_id: int):
    """
    指定されたIDの食事記録を削除する
    """
    with sqlite3.connect("meal_records.db") as conn:
        cursor = conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Meal record not found")
        return {"message": "Meal record deleted"}

# 特定の日付の食事記録を検索するエンドポイント
@app.get("/meals/date/{date}")
def get_meals_by_date(date: str):
    """
    指定された日付の食事記録をすべて取得する
    日付形式: YYYY-MM-DD
    """
    with sqlite3.connect("meal_records.db") as conn:
        meals = conn.execute(
            "SELECT * FROM meals WHERE date(date_time) = ? ORDER BY date_time",
            (date,)
        ).fetchall()
        return [{
            "id": m[0],
            "date_time": m[1],
            "meal_type": m[2],
            "food_name": m[3],
            "calories": m[4],
            "notes": m[5],
        } for m in meals]

# 特定の食事タイプの記録を検索するエンドポイント
@app.get("/meals/type/{meal_type}")
def get_meals_by_type(meal_type: str):
    """
    指定された食事タイプ（朝食、昼食など）の記録をすべて取得する
    """
    with sqlite3.connect("meal_records.db") as conn:
        meals = conn.execute(
            "SELECT * FROM meals WHERE meal_type = ? ORDER BY date_time DESC",
            (meal_type,)
        ).fetchall()
        return [{
            "id": m[0],
            "date_time": m[1],
            "meal_type": m[2],
            "food_name": m[3],
            "calories": m[4],
            "notes": m[5],
        } for m in meals]

# メインプログラムとして実行された場合の処理
if __name__ == "__main__":
    # FastAPIアプリケーションを非同期モードで起動
    uvicorn.run(app, host="0.0.0.0", port=8000)