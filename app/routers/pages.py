from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_recent_days
from app.database import get_db
from app.services import dashboard_service

router = APIRouter(tags=["pages"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def page_index(request: Request, db: Session = Depends(get_db)):
    """ダッシュボード画面（トップ）"""
    configured_recent_days = get_recent_days()
    summary = dashboard_service.get_dashboard_summary(db=db, recent_n=20, period_days=configured_recent_days)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_page": "dashboard",
            "summary": summary,
            "configured_recent_days": configured_recent_days,
        },
    )


@router.get("/setup", response_class=HTMLResponse)
async def page_setup(request: Request):
    """試験設定・開始画面"""
    return templates.TemplateResponse(
        request=request, name="setup.html", context={"active_page": "setup"}
    )


@router.get("/quiz", response_class=HTMLResponse)
async def page_quiz(request: Request, session_id: str = ""):
    """試験画面"""
    return templates.TemplateResponse(
        request=request,
        name="quiz.html",
        context={"session_id": session_id, "active_page": "quiz"},
    )


@router.get("/summary", response_class=HTMLResponse)
async def page_summary(request: Request, session_id: str = ""):
    """サマリー・結果画面"""
    return templates.TemplateResponse(
        request=request,
        name="summary.html",
        context={"session_id": session_id, "active_page": "summary"},
    )
