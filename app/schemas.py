from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    mode: str = Field(default="random", description="出題ジャンル (random, all_random, category_weak, question_weak)")
    question_count_target: int = Field(default=10, description="問題数 (10, 30, 50, -1)")


class CreateSessionResponse(BaseModel):
    session_id: str
    mode: str
    question_count_target: int


class OptionItem(BaseModel):
    id: str
    text: str
    explanation: Optional[str] = None


class NextQuestionResponse(BaseModel):
    session_id: str
    current_index: int
    target_count: int
    is_endless: bool
    question_id: str
    category_major: str
    category_minor: str
    question_type: str
    question_text: str
    options: List[OptionItem]


class SubmitAnswerRequest(BaseModel):
    question_id: str
    selected_answers: List[str] = Field(..., description="ユーザーが選択した表示記号リスト (例: ['A'])")


class SubmitAnswerResponse(BaseModel):
    is_correct: bool
    correct_answers: List[str]  # 表示用記号 (例: ['B'])
    explanation: str
    options: Optional[List[Dict[str, Any]]] = None
    has_next: bool
    total_answered: int
    target_count: int


class CategoryResultItem(BaseModel):
    major: str
    minor: str
    total: int
    correct: int
    rate: float


class IncorrectQuestionItem(BaseModel):
    id: str
    category_major: str
    category_minor: str
    question_text: str
    user_selected: List[str]
    user_selected_texts: List[str]
    correct_answers: List[str]
    correct_texts: List[str]
    explanation: str
    options: List[Dict[str, Any]]


class SessionSummaryResponse(BaseModel):
    session_id: str
    mode: str
    total_questions: int
    correct_count: int
    accuracy_rate: float
    is_passed: bool
    total_time_str: str
    avg_seconds: float
    category_results: List[CategoryResultItem]
    incorrect_questions: List[IncorrectQuestionItem]
