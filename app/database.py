from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# プロジェクトルートと storage/trainer.db のパス特定
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = STORAGE_DIR / "trainer.db"

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# SQLite用エンジンの作成 (connect_args に check_same_thread: False を設定)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI の Dependency 注入用ジェネレータ"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """テーブルの自動生成"""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
