import json
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import AnswerLog, Question, Session as DbSession

# インメモリでセッションごとの進行状態（出題済み問題リスト、現在の選択肢マッピング）を保持
# {session_id: {"asked_question_ids": set(), "current_question": {...}}}
_session_runtime_state: Dict[str, Dict[str, Any]] = {}


def create_quiz_session(db: Session, mode: str, question_count_target: int) -> DbSession:
    """新しい試験セッションを作成する"""
    session_id = str(uuid.uuid4())
    db_session = DbSession(
        id=session_id,
        mode=mode,
        question_count_target=question_count_target,
        started_at=datetime.now(timezone.utc),
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    _session_runtime_state[session_id] = {
        "asked_question_ids": [],
        "current_question": None,
    }

    return db_session


def get_available_question_candidates(db: Session, mode: str, exclude_ids: List[str]) -> List[Question]:
    """出題モードに応じた問題候補を取得する"""
    query = db.query(Question)
    if exclude_ids:
        query = query.filter(Question.id.not_in(exclude_ids))

    all_candidates = query.all()
    if not all_candidates:
        # すべて出題し尽くした場合、exclude_ids をリセットして再取得（エンドレス等）
        if exclude_ids:
            all_candidates = db.query(Question).all()

    if not all_candidates:
        return []

    if mode == "all_random":
        random.shuffle(all_candidates)
        return all_candidates

    elif mode == "random":
        # カテゴリ（大分類・中分類）から均等に選ぶため、カテゴリごとにグループ化
        by_category: Dict[Tuple[str, str], List[Question]] = {}
        for q in all_candidates:
            cat_key = (q.category_major, q.category_minor)
            by_category.setdefault(cat_key, []).append(q)

        # 各カテゴリからランダムに1問ずつピックアップして混ぜる
        interleaved: List[Question] = []
        cat_keys = list(by_category.keys())
        random.shuffle(cat_keys)

        for cat in cat_keys:
            random.shuffle(by_category[cat])

        max_len = max(len(v) for v in by_category.values())
        for i in range(max_len):
            for cat in cat_keys:
                if i < len(by_category[cat]):
                    interleaved.append(by_category[cat][i])

        return interleaved

    elif mode == "category_weak":
        # 直近の正解率が低いカテゴリを優先
        # 各カテゴリの直近回答ログを集計
        cat_stats: Dict[str, Dict[str, Any]] = {}  # {minor: {total: x, correct: y}}
        recent_logs = (
            db.query(AnswerLog, Question.category_minor)
            .join(Question, AnswerLog.question_id == Question.id)
            .order_by(desc(AnswerLog.answered_at))
            .limit(200)
            .all()
        )

        for log, minor in recent_logs:
            if minor not in cat_stats:
                cat_stats[minor] = {"total": 0, "correct": 0}
            cat_stats[minor]["total"] += 1
            if log.is_correct:
                cat_stats[minor]["correct"] += 1

        # 正解率スコアを計算 (未回答のカテゴリは優先度最高として正解率0扱い)
        def get_cat_score(q: Question) -> float:
            minor = q.category_minor
            if minor not in cat_stats or cat_stats[minor]["total"] == 0:
                return -1.0  # まだ解いたことがないカテゴリ
            stat = cat_stats[minor]
            return stat["correct"] / stat["total"]

        # 正解率が低い順にソート（同率ならランダム）
        random.shuffle(all_candidates)
        all_candidates.sort(key=get_cat_score)
        return all_candidates

    elif mode == "question_weak":
        # 直近3回の回答で正解率が50%未満の問題、または直近で間違えた問題
        # 各問題IDごとの直近回答を取得
        recent_logs = (
            db.query(AnswerLog)
            .order_by(desc(AnswerLog.answered_at))
            .all()
        )

        q_history: Dict[str, List[bool]] = {}
        for log in recent_logs:
            if log.question_id not in q_history:
                q_history[log.question_id] = []
            if len(q_history[log.question_id]) < 3:
                q_history[log.question_id].append(bool(log.is_correct))

        weak_ids = set()
        for q_id, results in q_history.items():
            if not results:
                continue
            # 直近で間違えた (直近1回がFalse) または 直近3回で正解率 < 50%
            rate = sum(1 for r in results if r) / len(results)
            if (not results[0]) or rate < 0.5:
                weak_ids.add(q_id)

        weak_candidates = [q for q in all_candidates if q.id in weak_ids]
        random.shuffle(weak_candidates)
        return weak_candidates

    else:
        # デフォルトはランダム
        random.shuffle(all_candidates)
        return all_candidates


def get_next_question(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
    """セッションの次の問題を取得し、選択肢をシャッフルして返す"""
    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not db_session:
        return None

    state = _session_runtime_state.setdefault(
        session_id, {"asked_question_ids": [], "current_question": None}
    )

    # 既に目標問題数に達しているかチェック
    answered_count = len(state["asked_question_ids"])
    if db_session.question_count_target > 0 and answered_count >= db_session.question_count_target:
        return None

    # まだ未回答の出題中問題があれば、リロールせずそのまま返す（F5リロード対策）
    curr = state.get("current_question")
    if curr and curr.get("question_id") not in state["asked_question_ids"]:
        return {
            "session_id": session_id,
            "current_index": answered_count + 1,
            "target_count": db_session.question_count_target,
            "is_endless": db_session.question_count_target == -1,
            "question_id": curr["question_id"],
            "category_major": curr["category_major"],
            "category_minor": curr["category_minor"],
            "question_type": curr["question_type"],
            "question_text": curr["question_text"],
            "options": curr["options"],
        }

    candidates = get_available_question_candidates(
        db, mode=db_session.mode, exclude_ids=state["asked_question_ids"]
    )

    if not candidates:
        return None

    chosen_question = candidates[0]

    # 選択肢をパースしてシャッフル
    try:
        raw_options = json.loads(chosen_question.options)
    except Exception:
        raw_options = []

    try:
        raw_correct_answers = json.loads(chosen_question.correct_answers)
    except Exception:
        raw_correct_answers = []

    # 選択肢をシャッフル
    shuffled_options_raw = list(raw_options)
    random.shuffle(shuffled_options_raw)

    # 表示用記号 (A, B, C, D, E, F...) を新たに付与
    letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
    shuffled_display_options = []
    display_options_with_explanation = []
    display_to_original: Dict[str, str] = {}
    original_to_display: Dict[str, str] = {}

    for idx, opt in enumerate(shuffled_options_raw):
        disp_letter = letters[idx] if idx < len(letters) else str(idx + 1)
        orig_id = opt.get("id", disp_letter)
        display_to_original[disp_letter] = orig_id
        original_to_display[orig_id] = disp_letter
        shuffled_display_options.append({
            "id": disp_letter,
            "text": opt.get("text", ""),
        })
        display_options_with_explanation.append({
            "id": disp_letter,
            "text": opt.get("text", ""),
            "is_correct": orig_id in raw_correct_answers,
            "explanation": opt.get("explanation", ""),
        })

    # 表示順における正解記号リスト（例: ["B"]）
    shuffled_correct_answers = [
        original_to_display[orig_id]
        for orig_id in raw_correct_answers
        if orig_id in original_to_display
    ]
    shuffled_correct_answers.sort()

    current_idx = answered_count + 1

    # サーバー状態に保持（解答判定時に利用）
    state["current_question"] = {
        "question_id": chosen_question.id,
        "question_text": chosen_question.question_text,
        "question_type": chosen_question.question_type,
        "raw_correct_answers": raw_correct_answers,
        "shuffled_correct_answers": shuffled_correct_answers,
        "display_to_original": display_to_original,
        "original_to_display": original_to_display,
        "explanation": chosen_question.explanation,
        "category_major": chosen_question.category_major,
        "category_minor": chosen_question.category_minor,
        "options": shuffled_display_options,
        "display_options_with_explanation": display_options_with_explanation,
    }

    return {
        "session_id": session_id,
        "current_index": current_idx,
        "target_count": db_session.question_count_target,
        "is_endless": db_session.question_count_target == -1,
        "question_id": chosen_question.id,
        "category_major": chosen_question.category_major,
        "category_minor": chosen_question.category_minor,
        "question_type": chosen_question.question_type,
        "question_text": chosen_question.question_text,
        "options": shuffled_display_options,
    }


def submit_answer(
    db: Session, session_id: str, question_id: str, selected_display_answers: List[str]
) -> Dict[str, Any]:
    """回答を受信し、判定してログに記録し結果を返す"""
    state = _session_runtime_state.get(session_id)
    if not state or not state.get("current_question"):
        raise ValueError("現在出題中の問題が存在しません。")

    curr = state["current_question"]
    if curr["question_id"] != question_id:
        raise ValueError("出題中の問題IDと一致しません。")

    # 判定
    shuffled_correct = set(curr["shuffled_correct_answers"])
    selected_set = set(selected_display_answers)
    is_correct = (selected_set == shuffled_correct)

    # 元の選択肢IDに変換して記録
    original_selected = [
        curr["display_to_original"].get(ans, ans) for ans in selected_display_answers
    ]

    log = AnswerLog(
        session_id=session_id,
        question_id=question_id,
        selected_answers=json.dumps(original_selected, ensure_ascii=False),
        is_correct=is_correct,
        answered_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()

    # 出題済みリストに追加
    state["asked_question_ids"].append(question_id)

    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    has_next = True
    if db_session and db_session.question_count_target > 0:
        if len(state["asked_question_ids"]) >= db_session.question_count_target:
            has_next = False

    return {
        "is_correct": is_correct,
        "correct_answers": curr["shuffled_correct_answers"],  # 表示用のA, Bなど
        "explanation": curr["explanation"],
        "options": curr.get("display_options_with_explanation", []),
        "has_next": has_next,
        "total_answered": len(state["asked_question_ids"]),
        "target_count": db_session.question_count_target if db_session else 0,
    }


def complete_quiz_session(db: Session, session_id: str) -> Dict[str, Any]:
    """セッションを完了し、サマリーデータを集計して返す"""
    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not db_session:
        raise ValueError("指定されたセッションが存在しません。")

    now = datetime.now(timezone.utc)
    if not db_session.completed_at:
        db_session.completed_at = now
        db.commit()

    # 回答ログ集計
    logs = (
        db.query(AnswerLog, Question)
        .join(Question, AnswerLog.question_id == Question.id)
        .filter(AnswerLog.session_id == session_id)
        .order_by(AnswerLog.id)
        .all()
    )

    total_questions = len(logs)
    correct_count = sum(1 for log, _ in logs if log.is_correct)
    accuracy_rate = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0.0

    # 所要時間の算出
    started_at = db_session.started_at
    completed_at = db_session.completed_at or now
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)

    total_seconds = max(1, int((completed_at - started_at).total_seconds()))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    time_str = f"{minutes}分 {seconds:02d}秒" if minutes > 0 else f"{seconds}秒"

    avg_seconds_per_question = round(total_seconds / total_questions, 1) if total_questions > 0 else 0

    # カテゴリ別正解率
    cat_summary: Dict[str, Dict[str, Any]] = {}
    for log, q in logs:
        minor = q.category_minor
        if minor not in cat_summary:
            cat_summary[minor] = {
                "major": q.category_major,
                "minor": minor,
                "total": 0,
                "correct": 0,
            }
        cat_summary[minor]["total"] += 1
        if log.is_correct:
            cat_summary[minor]["correct"] += 1

    category_results = []
    for cat in cat_summary.values():
        rate = round(cat["correct"] / cat["total"] * 100, 1) if cat["total"] > 0 else 0
        category_results.append({
            "major": cat["major"],
            "minor": cat["minor"],
            "total": cat["total"],
            "correct": cat["correct"],
            "rate": rate,
        })

    # 間違えた問題の復習リスト
    incorrect_questions = []
    for log, q in logs:
        if not log.is_correct:
            try:
                raw_options = json.loads(q.options)
            except Exception:
                raw_options = []
            try:
                raw_correct = json.loads(q.correct_answers)
            except Exception:
                raw_correct = []
            try:
                user_selected = json.loads(log.selected_answers)
            except Exception:
                user_selected = []

            # 選択肢ID -> テキスト マッピング
            opt_map = {opt.get("id"): opt.get("text") for opt in raw_options}

            incorrect_questions.append({
                "id": q.id,
                "category_major": q.category_major,
                "category_minor": q.category_minor,
                "question_text": q.question_text,
                "user_selected": user_selected,
                "user_selected_texts": [f"{k}: {opt_map.get(k, '')}" for k in user_selected],
                "correct_answers": raw_correct,
                "correct_texts": [f"{k}: {opt_map.get(k, '')}" for k in raw_correct],
                "explanation": q.explanation,
                "options": raw_options,
            })

    # クリーンアップ
    _session_runtime_state.pop(session_id, None)

    return {
        "session_id": session_id,
        "mode": db_session.mode,
        "total_questions": total_questions,
        "correct_count": correct_count,
        "accuracy_rate": accuracy_rate,
        "is_passed": accuracy_rate >= 72.0,  # AWS SAA 合格ライン（通常約72%）
        "total_time_str": time_str,
        "avg_seconds": avg_seconds_per_question,
        "category_results": category_results,
        "incorrect_questions": incorrect_questions,
    }
