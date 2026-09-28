import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Question, SystemMetadata

logger = logging.getLogger("trainer.sync")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_paths() -> Tuple[Path, Path, Path]:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    categories_file = data_dir / "categories.json"
    questions_dir = data_dir / "questions"
    return base_dir, categories_file, questions_dir


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"JSON読み込み失敗 ({path.name}): {e}")
        return None


def sync_questions_to_db(db: Session, force: bool = False) -> Dict[str, Any]:
    """
    JSON問題マスターデータをSQLiteに二段階差分同期する。
    戻り値: 同期結果統計
    """
    _, categories_file, questions_dir = get_paths()

    stats = {
        "status": "skipped",
        "inserted": 0,
        "updated": 0,
        "total_in_db": 0,
        "reason": "",
    }

    if not categories_file.is_file():
        logger.warning(f"categories.json が見つかりません: {categories_file}")
        stats["reason"] = "categories.json not found"
        return stats

    cat_data = load_json(categories_file)
    if not cat_data:
        stats["reason"] = "categories.json is empty or invalid"
        return stats

    cat_updated_at = cat_data.get("updated_at", "")

    # 第1段階: categories.json の updated_at と DB の最終同期日時を比較
    meta = db.query(SystemMetadata).filter(SystemMetadata.key == "last_synced_categories_at").first()
    db_question_count = db.query(Question).count()

    if not force and meta and meta.value == cat_updated_at and db_question_count > 0:
        logger.info(f"問題データは最新です (同期スキップ: {cat_updated_at}, DB登録数: {db_question_count}問)")
        stats["status"] = "skipped"
        stats["total_in_db"] = db_question_count
        stats["reason"] = "already up to date"
        return stats

    logger.info("問題データの差分同期を開始します...")
    inserted_count = 0
    updated_count = 0

    # 既存の全問題の updated_at を取得してメモリ上で差分判定（高速化）
    existing_questions = {q.id: q.updated_at for q in db.query(Question.id, Question.updated_at).all()}

    # questions 配下の全 .json を走査
    for file_path in sorted(questions_dir.rglob("*.json")):
        if file_path.name in ("index.json", "sample.json"):
            continue

        q_data = load_json(file_path)
        if not q_data:
            continue

        q_id = q_data.get("id") or file_path.stem
        q_major = q_data.get("category_major", "")
        q_minor = q_data.get("category_minor", "")
        q_type = q_data.get("question_type", "single")
        q_text = q_data.get("question_text", "")
        options = q_data.get("options", [])
        correct_answers = q_data.get("correct_answers", [])
        explanation = q_data.get("explanation", "")

        # 更新日時判定: JSON内の updated_at またはファイルのmtime
        if "updated_at" in q_data and q_data["updated_at"]:
            file_updated_at = q_data["updated_at"]
        else:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            file_updated_at = mtime.strftime("%Y-%m-%dT%H:%M:%SZ")

        options_json = json.dumps(options, ensure_ascii=False)
        correct_json = json.dumps(correct_answers, ensure_ascii=False)

        if q_id not in existing_questions:
            # 新規挿入
            new_q = Question(
                id=q_id,
                category_major=q_major,
                category_minor=q_minor,
                question_type=q_type,
                question_text=q_text,
                options=options_json,
                correct_answers=correct_json,
                explanation=explanation,
                updated_at=file_updated_at,
            )
            db.add(new_q)
            inserted_count += 1
        elif force or existing_questions[q_id] != file_updated_at:
            # 更新
            target_q = db.query(Question).filter(Question.id == q_id).first()
            if target_q:
                target_q.category_major = q_major
                target_q.category_minor = q_minor
                target_q.question_type = q_type
                target_q.question_text = q_text
                target_q.options = options_json
                target_q.correct_answers = correct_json
                target_q.explanation = explanation
                target_q.updated_at = file_updated_at
                updated_count += 1

    # システムメタデータの更新
    if not meta:
        meta = SystemMetadata(
            key="last_synced_categories_at",
            value=cat_updated_at,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(meta)
    else:
        meta.value = cat_updated_at
        meta.updated_at = datetime.now(timezone.utc)

    db.commit()

    total_count = db.query(Question).count()
    logger.info(
        f"問題データ同期完了: 新規追加 {inserted_count} 件, 更新 {updated_count} 件 (DB合計: {total_count}問)"
    )

    stats["status"] = "synced"
    stats["inserted"] = inserted_count
    stats["updated"] = updated_count
    stats["total_in_db"] = total_count
    return stats


def rebuild_catalog_indexes():
    """scripts/sync_questions.py の処理を実行してインデックスを再構築"""
    from scripts import sync_questions

    _, categories_file, questions_dir = get_paths()
    logger.info("目録（index.json & categories.json）の再構築を開始します...")
    sync_questions.run_step1(questions_dir=questions_dir, dry_run=False)
    sync_questions.run_step2(questions_dir=questions_dir, categories_file=categories_file, dry_run=False)
    sync_questions.update_categories_catalog(categories_file=categories_file, questions_dir=questions_dir, dry_run=False)
    logger.info("目録の再構築が完了しました。")


def main():
    parser = argparse.ArgumentParser(description="JSON問題マスターからSQLiteへの同期スクリプト")
    parser.add_argument("--force", action="store_true", help="差分判定を無視して強制的に全問UPSERT同期")
    parser.add_argument("--rebuild-catalog", action="store_true", help="問題UUID検査およびindex.json/categories.jsonの再構築を実行")

    args = parser.parse_args()

    init_db()

    if args.rebuild-catalog if hasattr(args, "rebuild-catalog") else args.rebuild_catalog:
        rebuild_catalog_indexes()

    with SessionLocal() as db:
        sync_questions_to_db(db, force=args.force)


if __name__ == "__main__":
    main()
