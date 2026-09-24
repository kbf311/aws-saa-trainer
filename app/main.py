import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.database import SessionLocal, init_db
from app.routers import dashboard, pages, quiz
from app.sync import sync_questions_to_db

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trainer.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーション起動時の初期化処理:
    1. SQLite データベースおよびテーブルの自動作成
    2. JSON問題マスター ➔ SQLite の差分同期実行（二段階判定）
    """
    logger.info("==================================================")
    logger.info("AWS SAA-C03 Trainer を起動しています...")
    logger.info("==================================================")

    # 1. DB・テーブル自動作成
    init_db()
    logger.info("SQLite データベースおよびテーブルを初期化しました。")

    # 2. 差分同期判定 & 実行
    with SessionLocal() as db:
        sync_result = sync_questions_to_db(db=db, force=False)
        logger.info(f"起動時データ同期ステータス: {sync_result['status']} ({sync_result['reason'] or 'completed'})")

    yield

    logger.info("AWS SAA-C03 Trainer を終了します。")


app = FastAPI(
    title="AWS SAA-C03 Trainer",
    description="AWS Certified Solutions Architect - Associate 認定対策 高機能トレーニングアプリ",
    version="1.0.0",
    lifespan=lifespan,
)

# 静的ファイルの提供
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ルーター登録
app.include_router(pages.router)
app.include_router(quiz.router)
app.include_router(dashboard.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

