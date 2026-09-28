"""過去の日付から現在までのダミー回答履歴データを生成するスクリプト

使用例:
    python scripts/generate_dummy_answers.py
    python scripts/generate_dummy_answers.py --days 100 --clear
    python scripts/generate_dummy_answers.py --days 60 --min-per-day 10 --max-per-day 30
"""

import argparse
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Windowsコンソールでの文字化け防止
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# プロジェクトルートを sys.path に追加
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


from app.database import SessionLocal, init_db
from app.models import AnswerLog, Question, Session as DbSession


def pick_answers(question: Question, is_correct: bool) -> str:
    """正解/不正解に応じた選択肢IDリストのJSON文字列を生成"""
    try:
        correct_list = json.loads(question.correct_answers)
        if not isinstance(correct_list, list):
            correct_list = [str(correct_list)]
    except Exception:
        correct_list = ["A"]

    if is_correct:
        return json.dumps(correct_list)

    # 不正解の場合
    try:
        options = json.loads(question.options)
        all_option_ids = [opt.get("id") for opt in options if isinstance(opt, dict) and "id" in opt]
    except Exception:
        all_option_ids = ["A", "B", "C", "D"]

    wrong_option_ids = [oid for oid in all_option_ids if oid not in correct_list]
    if wrong_option_ids:
        pick_count = min(len(correct_list), len(wrong_option_ids))
        picked = random.sample(wrong_option_ids, max(1, pick_count))
        return json.dumps(picked)

    # 正解以外の選択肢が見つからない場合のフォールバック
    return json.dumps(["X"])


def generate_dummy_data(
    days: int = 100,
    clear_existing: bool = False,
    min_jump: int = 1,
    max_jump: int = 4,
    min_per_day: int = 5,
    max_per_day: int = 25,
    seed: int = None,
):
    if seed is not None:
        random.seed(seed)

    init_db()
    db = SessionLocal()

    try:
        # 問題が存在するか確認
        questions = db.query(Question).all()
        if not questions:
            print("エラー: questions テーブルに問題が1件も存在しません。")
            print("先に python scripts/sync_questions.py を実行して問題を同期してください。")
            return

        print(f"利用可能な問題数: {len(questions)} 問")

        if clear_existing:
            print("既存の回答履歴（AnswerLog / Session）を削除しています...")
            db.query(AnswerLog).delete()
            db.query(DbSession).delete()
            db.commit()
            print("既存データをクリアしました。")

        # 現在時刻（UTC基準）
        now_utc = datetime.now(timezone.utc)
        current_date = (now_utc - timedelta(days=days)).date()
        target_end_date = now_utc.date()

        print(f"ダミーデータ生成開始:")
        print(f"  - 期間: {current_date} 〜 {target_end_date} (過去 {days} 日間)")
        print(f"  - 日付ジャンプ幅: {min_jump} 〜 {max_jump} 日")
        print(f"  - 1日あたり回答数: {min_per_day} 〜 {max_per_day} 問")

        total_sessions = 0
        total_answers = 0
        total_correct = 0

        modes = ["random", "all_random", "category_weak", "question_weak"]

        while current_date <= target_end_date:
            # 日数が進むにつれて正答率が緩やかに向上するシミュレーション（50% -> 85%）
            elapsed_days = (current_date - (now_utc - timedelta(days=days)).date()).days
            progress_ratio = min(1.0, max(0.0, elapsed_days / max(1, days)))
            # 基本正答率: 初日 50% 付近、最終日 85% 付近 (±10%の揺らぎ)
            base_accuracy = 0.50 + 0.35 * progress_ratio + random.uniform(-0.08, 0.08)
            base_accuracy = min(0.95, max(0.35, base_accuracy))

            # 本日の回答数
            day_question_count = random.randint(min_per_day, max_per_day)

            # 1〜2回に分けたセッションをシミュレート
            session_splits = []
            if day_question_count > 12 and random.random() < 0.4:
                split1 = day_question_count // 2
                split2 = day_question_count - split1
                session_splits = [split1, split2]
            else:
                session_splits = [day_question_count]

            # 時間帯の設定（1セッション目: 朝〜昼または夕方、2セッション目: 夜など）
            hour_candidates = [
                random.randint(7, 12),
                random.randint(18, 23),
            ]

            for s_idx, q_count in enumerate(session_splits):
                session_id = str(uuid.uuid4())
                mode = random.choice(modes)

                session_hour = hour_candidates[s_idx % len(hour_candidates)]
                session_minute = random.randint(0, 45)
                session_start_time = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    session_hour,
                    session_minute,
                    random.randint(0, 59),
                    tzinfo=timezone.utc,
                )

                # 今日の現在時刻を超えないようキャップ
                if session_start_time > now_utc:
                    session_start_time = now_utc - timedelta(minutes=random.randint(5, 60))

                session = DbSession(
                    id=session_id,
                    mode=mode,
                    question_count_target=q_count,
                    started_at=session_start_time.replace(tzinfo=None),
                    completed_at=None,
                )
                db.add(session)
                total_sessions += 1

                # 演習する問題をランダム選択（重複を許容して実際の学習に近づける）
                chosen_questions = random.choices(questions, k=q_count)

                current_time_cursor = session_start_time
                for q in chosen_questions:
                    # 解答にかかる時間 (15秒〜90秒)
                    ans_delta = timedelta(seconds=random.randint(15, 90))
                    current_time_cursor += ans_delta

                    if current_time_cursor > now_utc:
                        current_time_cursor = now_utc

                    is_correct = random.random() < base_accuracy
                    selected = pick_answers(q, is_correct)

                    log = AnswerLog(
                        session_id=session_id,
                        question_id=q.id,
                        selected_answers=selected,
                        is_correct=is_correct,
                        answered_at=current_time_cursor.replace(tzinfo=None),
                    )
                    db.add(log)
                    total_answers += 1
                    if is_correct:
                        total_correct += 1

                # セッション完了時刻の記録
                session.completed_at = current_time_cursor.replace(tzinfo=None)

            # 次の学習日へのジャンプ（ランダム）
            jump_days = random.randint(min_jump, max_jump)
            current_date += timedelta(days=jump_days)

        db.commit()

        accuracy = round(total_correct / total_answers * 100, 1) if total_answers > 0 else 0.0
        print("\n=== ダミーデータ生成完了 ===")
        print(f"作成セッション数 : {total_sessions} 件")
        print(f"作成回答ログ総数 : {total_answers} 件")
        print(f"正解数 / 不正解数: {total_correct} 件 / {total_answers - total_correct} 件")
        print(f"総合正解率       : {accuracy}%")
        print("============================")

    except Exception as e:
        db.rollback()
        print(f"エラーが発生したためロールバックしました: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="現在の日付から過去N日間のダミー回答履歴を作成します。")
    parser.add_argument(
        "--days",
        type=int,
        default=100,
        help="何日前から開始するか (デフォルト: 100)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="実行前に既存の回答ログ・セッションを全て削除する",
    )
    parser.add_argument(
        "--min-jump",
        type=int,
        default=1,
        help="次の学習日までの最小ジャンプ日数 (デフォルト: 1)",
    )
    parser.add_argument(
        "--max-jump",
        type=int,
        default=4,
        help="次の学習日までの最大ジャンプ日数 (デフォルト: 4)",
    )
    parser.add_argument(
        "--min-per-day",
        type=int,
        default=5,
        help="1日の最小回答数 (デフォルト: 5)",
    )
    parser.add_argument(
        "--max-per-day",
        type=int,
        default=25,
        help="1日の最大回答数 (デフォルト: 25)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="乱数シード値 (再現用)",
    )

    args = parser.parse_args()
    generate_dummy_data(
        days=args.days,
        clear_existing=args.clear,
        min_jump=args.min_jump,
        max_jump=args.max_jump,
        min_per_day=args.min_per_day,
        max_per_day=args.max_per_day,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
