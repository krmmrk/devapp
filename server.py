from fastapi import FastAPI, HTTPException  # FastAPIフレームワークとエラーハンドリング用
from fastapi.middleware.cors import CORSMiddleware  # CORS設定用
from fastapi.responses import HTMLResponse  # HTMLを返すためのレスポンスクラス
from pydantic import BaseModel  # データバリデーション用
from typing import Optional  # オプションのフィールドを扱うための型
from datetime import datetime  # 日時を扱うためのモジュール
import sqlite3  # SQLiteデータベース操作用
import uvicorn  # ASGIサーバーの起動用

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# CORS（Cross-Origin Resource Sharing）の設定
# フロントエンドからのAPIアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可（本番環境では制限を推奨）
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
                meal_type TEXT NOT NULL,              -- 食事の種類（朝食、昼食、夕食、間食など）
                food_name TEXT NOT NULL,              -- 食事の名前
                calories INTEGER,                     -- カロリー（オプション）
                date_time TIMESTAMP NOT NULL,         -- 食事の日時
                notes TEXT,                           -- メモ（オプション）
                image_url TEXT                        -- 食事の画像URL（オプション）
            )
            """
        )

# アプリケーション起動時にデータベースを初期化
init_db()

# 食事データのベースモデル定義
class Meal(BaseModel):
    meal_type: str  # 朝食、昼食、夕食、間食など
    food_name: str  # 食事の名前
    calories: Optional[int] = None  # カロリー（省略可能）
    date_time: datetime  # 食事した日時
    notes: Optional[str] = None  # メモ（省略可能）
    image_url: Optional[str] = None  # 食事の画像URL（省略可能）

# レスポンス用のモデル（IDフィールド追加）
class MealResponse(Meal):
    id: int

# クライアント用のHTMLを返すエンドポイント
@app.get("/", response_class=HTMLResponse)
def read_root():
    """クライアントページを提供する（HTMLファイルを読み込んで返す）"""
    with open("client.html", "r", encoding="utf-8") as f:
        return f.read()

# 新しい食事記録を作成するエンドポイント
@app.post("/meals", response_model=MealResponse)
def create_meal(meal: Meal):
    """新しい食事記録をデータベースに追加する"""
    with sqlite3.connect("meal_records.db") as conn:
        cursor = conn.execute(
            """
            INSERT INTO meals (meal_type, food_name, calories, date_time, notes, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (meal.meal_type, meal.food_name, meal.calories, meal.date_time.isoformat(), meal.notes, meal.image_url),
        )
        meal_id = cursor.lastrowid
        return {**meal.dict(), "id": meal_id}

# すべての食事記録を取得するエンドポイント
@app.get("/meals")
def get_meals():
    """すべての食事記録を取得する（日時の降順でソート）"""
    with sqlite3.connect("meal_records.db") as conn:
        meals = conn.execute("SELECT * FROM meals ORDER BY date_time DESC").fetchall()
        return [{
            "id": m[0], "meal_type": m[1], "food_name": m[2], "calories": m[3],
            "date_time": m[4], "notes": m[5], "image_url": m[6]
        } for m in meals]

# 特定のIDの食事記録を取得するエンドポイント
@app.get("/meals/{meal_id}")
def get_meal(meal_id: int):
    """指定されたIDの食事記録を取得する"""
    with sqlite3.connect("meal_records.db") as conn:
        meal = conn.execute("SELECT * FROM meals WHERE id = ?", (meal_id,)).fetchone()
        if not meal:
            raise HTTPException(status_code=404, detail="Meal record not found")
        return {
            "id": meal[0], "meal_type": meal[1], "food_name": meal[2], "calories": meal[3],
            "date_time": meal[4], "notes": meal[5], "image_url": meal[6]
        }

# 特定のIDの食事記録を削除するエンドポイント
@app.delete("/meals/{meal_id}")
def delete_meal(meal_id: int):
    """指定されたIDの食事記録を削除する"""
    with sqlite3.connect("meal_records.db") as conn:
        cursor = conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Meal record not found")
        return {"message": "Meal record deleted"}

# FastAPIアプリケーションを起動する（開発用）
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
