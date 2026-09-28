from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_data(
    recent_n: int = Query(20, ge=5, le=50, description="カテゴリー評価範囲（直近n問）"),
    period_days: Optional[int] = Query(None, ge=1, le=365, description="集計期間（直近n日）"),
    db: Session = Depends(get_db),
):
    """ダッシュボード用の全指標データを取得する（期間絞り込み対応）"""
    data = dashboard_service.get_dashboard_summary(db=db, recent_n=recent_n, period_days=period_days)
    return data


@router.get("/weak-questions")
def get_weak_questions(
    limit: int = Query(10, ge=1, le=50),
    period_days: Optional[int] = Query(None, ge=1, le=365, description="集計期間（直近n日）"),
    db: Session = Depends(get_db),
):
    """苦手問題リストを取得する"""
    return dashboard_service.get_weak_questions_summary(db=db, limit=limit, period_days=period_days)


@router.get("/session/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_db)):
    """指定された演習セッションの問題一覧と回答詳細を取得する"""
    detail = dashboard_service.get_session_detail(db=db, session_id=session_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたセッションが見つかりません。")
    return detail

