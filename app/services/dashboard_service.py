from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.config import get_recent_days
from app.models import AnswerLog, Question, Session as DbSession


def get_dashboard_summary(
    db: Session,
    recent_n: int = 20,
    period_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    ダッシュボード用の総合サマリーと各種指標をオンデマンド計算する。
    period_days が指定された場合は直近 n 日間のログを対象とし、None の場合は全期間を対象とする。
    """
    configured_recent_days = get_recent_days()

    # ユーザーローカル日時を基準に期間境界を算出
    now_local = datetime.now().astimezone()
    today_local = now_local.date()

    start_dt_utc: Optional[datetime] = None
    start_date_local = None
    if period_days is not None and period_days > 0:
        start_date_local = today_local - timedelta(days=period_days - 1)
        start_dt_local = datetime.combine(start_date_local, datetime.min.time(), tzinfo=now_local.tzinfo)
        start_dt_utc = start_dt_local.astimezone(timezone.utc).replace(tzinfo=None)

    period_filters = [AnswerLog.answered_at >= start_dt_utc] if start_dt_utc else []

    # 1. 通算学習日数（全期間）
    days_count = db.query(func.count(func.distinct(func.date(AnswerLog.answered_at)))).scalar() or 0

    # 2. 累計回答問題数 & 総合正解数（全期間）
    total_answers = db.query(func.count(AnswerLog.id)).scalar() or 0
    total_correct = db.query(func.count(AnswerLog.id)).filter(AnswerLog.is_correct.is_(True)).scalar() or 0
    overall_accuracy = round(total_correct / total_answers * 100, 1) if total_answers > 0 else 0.0

    # 直近 recent_n 問の正解率（全期間の直近 recent_n 問）
    recent_all_logs = (
        db.query(AnswerLog.is_correct)
        .order_by(desc(AnswerLog.answered_at))
        .limit(recent_n)
        .all()
    )
    recent_sample_count = len(recent_all_logs)
    recent_correct = sum(1 for (is_corr,) in recent_all_logs if is_corr)
    recent_accuracy = round(recent_correct / recent_sample_count * 100, 1) if recent_sample_count > 0 else 0.0

    # 本日の回答数（ユーザーローカルタイムゾーン基準）
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_local.astimezone(timezone.utc).replace(tzinfo=None)
    today_answers = db.query(func.count(AnswerLog.id)).filter(AnswerLog.answered_at >= today_start_utc).scalar() or 0

    # 最終学習日時
    last_log = (
        db.query(AnswerLog.answered_at)
        .order_by(desc(AnswerLog.answered_at))
        .first()
    )
    last_answered_at = None
    last_learned_date = None
    if last_log and last_log[0]:
        dt = last_log[0]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone()
        last_answered_at = dt.isoformat()
        last_learned_date = dt_local.strftime("%Y-%m-%d")

    # 3. 累計回答推移（日付ごとの累積回答数）
    daily_query = (
        db.query(func.date(AnswerLog.answered_at).label("day"), func.count(AnswerLog.id).label("cnt"))
        .group_by(func.date(AnswerLog.answered_at))
        .order_by("day")
    )
    if start_dt_utc:
        daily_query = daily_query.filter(AnswerLog.answered_at >= start_dt_utc)

    daily_counts = daily_query.all()
    day_counts_map = {}
    for day_val, cnt in daily_counts:
        day_key = day_val.strftime("%Y-%m-%d") if hasattr(day_val, "strftime") else str(day_val)
        day_counts_map[day_key] = cnt

    history_labels = []
    cumulative_data = []
    daily_data = []
    running_total = 0

    if period_days is not None and period_days > 0 and start_date_local:
        # 指定期間の開始前時点での通算回答数（prior_total）を取得してベースとする
        prior_total = (
            db.query(func.count(AnswerLog.id))
            .filter(AnswerLog.answered_at < start_dt_utc)
            .scalar()
            or 0
        )
        running_total = prior_total

        # 指定期間開始の前日時点（ベース累計値）
        prev_date_str = (start_date_local - timedelta(days=1)).strftime("%Y-%m-%d")
        history_labels.append(prev_date_str)
        cumulative_data.append(running_total)
        daily_data.append(0)

        # 学習していない日はプロットせず、回答があった日のみをプロット
        if daily_counts:
            for day_val, cnt in daily_counts:
                running_total += cnt
                day_str = day_val.strftime("%Y-%m-%d") if hasattr(day_val, "strftime") else str(day_val)
                history_labels.append(day_str)
                cumulative_data.append(running_total)
                daily_data.append(cnt)
        else:
            today_str = today_local.strftime("%Y-%m-%d")
            history_labels.append(today_str)
            cumulative_data.append(running_total)
            daily_data.append(0)
    else:
        # 全期間の場合
        if daily_counts:
            first_day_val = daily_counts[0][0]
            if isinstance(first_day_val, str):
                first_date = datetime.strptime(first_day_val, "%Y-%m-%d").date()
            elif hasattr(first_day_val, "strftime"):
                first_date = first_day_val
            else:
                first_date = datetime.strptime(str(first_day_val), "%Y-%m-%d").date()

            prev_date_str = (first_date - timedelta(days=1)).strftime("%Y-%m-%d")
            history_labels.append(prev_date_str)
            cumulative_data.append(0)
            daily_data.append(0)

            for day, cnt in daily_counts:
                running_total += cnt
                day_str = day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)
                history_labels.append(day_str)
                cumulative_data.append(running_total)
                daily_data.append(cnt)

    # 4. カテゴリー別 正解率分析（直近 n 問）
    categories = (
        db.query(Question.category_major, Question.category_minor)
        .distinct()
        .order_by(Question.category_major, Question.category_minor)
        .all()
    )

    category_stats = []
    for major, minor in categories:
        q_filter = [
            Question.category_major == major,
            Question.category_minor == minor,
        ]
        if start_dt_utc:
            q_filter.append(AnswerLog.answered_at >= start_dt_utc)

        recent_logs = (
            db.query(AnswerLog.is_correct)
            .join(Question, AnswerLog.question_id == Question.id)
            .filter(*q_filter)
            .order_by(desc(AnswerLog.answered_at))
            .limit(recent_n)
            .all()
        )

        sampled_count = len(recent_logs)
        correct_count = sum(1 for (is_corr,) in recent_logs if is_corr)
        rate = round(correct_count / sampled_count * 100, 1) if sampled_count > 0 else 0.0

        category_stats.append({
            "major": major,
            "minor": minor,
            "sample_count": sampled_count,
            "correct_count": correct_count,
            "rate": rate,
            "has_data": sampled_count > 0,
        })

    # 5. 学習ヒートマップ用データ（通算日別回答数）
    all_daily_counts = (
        db.query(func.date(AnswerLog.answered_at).label("day"), func.count(AnswerLog.id).label("cnt"))
        .group_by(func.date(AnswerLog.answered_at))
        .all()
    )
    heatmap_data = {
        (day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)): cnt
        for day, cnt in all_daily_counts
    }

    # 6. 演習セッション履歴（直近5件）
    session_query = db.query(DbSession).order_by(desc(DbSession.started_at))
    if start_dt_utc:
        session_query = session_query.filter(DbSession.started_at >= start_dt_utc)
    recent_sessions = session_query.limit(5).all()

    sessions_data = []
    for s in recent_sessions:
        s_logs = db.query(AnswerLog).filter(AnswerLog.session_id == s.id).all()
        q_count = len(s_logs)
        c_count = sum(1 for log in s_logs if log.is_correct)
        acc = round(c_count / q_count * 100, 1) if q_count > 0 else 0.0
        sessions_data.append({
            "id": s.id,
            "mode": s.mode,
            "target": s.question_count_target,
            "answered": q_count,
            "correct": c_count,
            "rate": acc,
            "started_at": s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "",
            "is_completed": s.completed_at is not None,
        })

    # 利用可能な年一覧を取得
    distinct_years = (
        db.query(func.strftime("%Y", AnswerLog.answered_at).label("yr"))
        .filter(AnswerLog.answered_at.is_not(None))
        .distinct()
        .order_by(desc("yr"))
        .all()
    )
    available_years = [int(y[0]) for y in distinct_years if y[0] and str(y[0]).isdigit()]
    current_year = now_local.year
    if current_year not in available_years:
        available_years.insert(0, current_year)
    if (current_year - 1) not in available_years:
        available_years.append(current_year - 1)
    available_years.sort(reverse=True)

    return {
        "days_count": days_count,
        "total_answers": total_answers,
        "total_correct": total_correct,
        "overall_accuracy": overall_accuracy,
        "recent_accuracy": recent_accuracy,
        "recent_sample_count": recent_sample_count,
        "today_answers": today_answers,
        "last_answered_at": last_answered_at,
        "last_learned_date": last_learned_date,
        "recent_n": recent_n,
        "period_days": period_days,
        "configured_recent_days": configured_recent_days,
        "available_years": available_years,
        "current_year": current_year,
        "cumulative_history": {
            "labels": history_labels,
            "cumulative": cumulative_data,
            "daily": daily_data,
        },
        "category_stats": category_stats,
        "heatmap": heatmap_data,
        "recent_sessions": sessions_data,
    }


def get_weak_questions_summary(db: Session, limit: int = 10, period_days: Optional[int] = None) -> List[Dict[str, Any]]:
    """直近で間違えた問題または正解率が低い問題のリストを取得"""
    query = (
        db.query(AnswerLog, Question)
        .join(Question, AnswerLog.question_id == Question.id)
        .order_by(desc(AnswerLog.answered_at))
    )

    if period_days is not None and period_days > 0:
        now_local = datetime.now().astimezone()
        start_date_local = now_local.date() - timedelta(days=period_days - 1)
        start_dt_local = datetime.combine(start_date_local, datetime.min.time(), tzinfo=now_local.tzinfo)
        start_dt_utc = start_dt_local.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(AnswerLog.answered_at >= start_dt_utc)

    logs = query.all()

    q_map = defaultdict(lambda: {"total": 0, "correct": 0, "question": None, "last_result": None})
    for log, q in logs:
        entry = q_map[q.id]
        if entry["question"] is None:
            entry["question"] = q
            entry["last_result"] = log.is_correct
        entry["total"] += 1
        if log.is_correct:
            entry["correct"] += 1

    weak_list = []
    for q_id, data in q_map.items():
        q = data["question"]
        total = data["total"]
        correct = data["correct"]
        rate = round(correct / total * 100, 1) if total > 0 else 0.0

        if not data["last_result"] or rate < 60.0:
            weak_list.append({
                "id": q.id,
                "category_major": q.category_major,
                "category_minor": q.category_minor,
                "question_text": q.question_text[:120] + ("..." if len(q.question_text) > 120 else ""),
                "total_answered": total,
                "correct_count": correct,
                "rate": rate,
                "last_result": data["last_result"],
            })

    weak_list.sort(key=lambda x: (x["last_result"], x["rate"]))
    return weak_list[:limit]

