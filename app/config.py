import os
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("trainer.config")

# プロジェクトルートディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
ENV_SAMPLE_PATH = BASE_DIR / ".env.sample"

def ensure_env_file() -> None:
    """
    .env ファイルが存在しない場合、.env.sample をコピーして作成する。
    """
    if not ENV_PATH.exists():
        if ENV_SAMPLE_PATH.exists():
            try:
                shutil.copy(ENV_SAMPLE_PATH, ENV_PATH)
                logger.info(f".env が存在しなかったため、{ENV_SAMPLE_PATH} から作成しました。")
            except Exception as e:
                logger.warning(f".env.sample のコピーに失敗しました: {e}")
        else:
            logger.warning(f".env も .env.sample も見つかりませんでした: {ENV_PATH}")

# 起動・インポート時に .env の存在を保証し、読み込む
ensure_env_file()
load_dotenv(dotenv_path=ENV_PATH)

def get_recent_days() -> int:
    """
    ダッシュボードで利用する「直近 n 日」の日数を取得する。
    環境変数 RECENT_DAYS を参照し、無効な値の場合はデフォルト 7 を返す。
    """
    # 実行時に環境変数が再読み込みされるよう、都度取得
    raw_val = os.getenv("RECENT_DAYS", "7")
    try:
        val = int(raw_val)
        return val if val > 0 else 7
    except (ValueError, TypeError):
        return 7
