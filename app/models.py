from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, index=True)
    category_major = Column(String(255), nullable=False)
    category_minor = Column(String(255), nullable=False)
    question_type = Column(String(50), nullable=False, default="single")
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON string: list of {id, text}
    correct_answers = Column(Text, nullable=False)  # JSON string: list of ids e.g. ["B"]
    explanation = Column(Text, nullable=False)
    updated_at = Column(String(50), nullable=False)  # ISO8601 string or timestamp

    # リレーション
    answer_logs = relationship("AnswerLog", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_questions_category", "category_major", "category_minor"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, index=True)
    mode = Column(String(50), nullable=False)  # random, all_random, category_weak, question_weak, etc.
    question_count_target = Column(Integer, nullable=False)  # 10, 30, 50, -1
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # リレーション
    answer_logs = relationship("AnswerLog", back_populates="session", cascade="all, delete-orphan")


class AnswerLog(Base):
    __tablename__ = "answer_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    selected_answers = Column(Text, nullable=False)  # JSON string e.g. ["B"]
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=utc_now, nullable=False)

    # リレーション
    session = relationship("Session", back_populates="answer_logs")
    question = relationship("Question", back_populates="answer_logs")

    __table_args__ = (
        Index("idx_answer_logs_question_id", "question_id"),
        Index("idx_answer_logs_session_id", "session_id"),
        Index("idx_answer_logs_answered_at", "answered_at"),
    )


class SystemMetadata(Base):
    __tablename__ = "system_metadata"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
