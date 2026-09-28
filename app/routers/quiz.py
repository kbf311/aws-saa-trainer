from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    NextQuestionResponse,
    SessionSummaryResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services import quiz_service

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/session", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    """演習セッションを新しく開始する"""
    session = quiz_service.create_quiz_session(
        db=db, mode=req.mode, question_count_target=req.question_count_target
    )
    return CreateSessionResponse(
        session_id=session.id,
        mode=session.mode,
        question_count_target=session.question_count_target,
    )


@router.get("/session/{session_id}/next", response_model=NextQuestionResponse)
def get_next_question(session_id: str, db: Session = Depends(get_db)):
    """セッションの次の問題を取得する（選択肢はシャッフル済み）"""
    question_data = quiz_service.get_next_question(db=db, session_id=session_id)
    if not question_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="次の問題が存在しないか、目標問題数に達しました。",
        )
    return NextQuestionResponse(**question_data)


@router.post("/session/{session_id}/answer", response_model=SubmitAnswerResponse)
def submit_answer(
    session_id: str, req: SubmitAnswerRequest, db: Session = Depends(get_db)
):
    """解答を送信して即時判定結果と解説を取得する"""
    try:
        result = quiz_service.submit_answer(
            db=db,
            session_id=session_id,
            question_id=req.question_id,
            selected_display_answers=req.selected_answers,
        )
        return SubmitAnswerResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/session/{session_id}/complete", response_model=SessionSummaryResponse)
def complete_session(session_id: str, db: Session = Depends(get_db)):
    """セッションを完了し、サマリー（結果）を取得する"""
    try:
        summary = quiz_service.complete_quiz_session(db=db, session_id=session_id)
        return SessionSummaryResponse(**summary)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
