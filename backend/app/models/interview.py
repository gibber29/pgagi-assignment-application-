from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True)
    role = Column(String, nullable=True)
    status = Column(String, default="awaiting_resume", nullable=False)
    resume = Column(JSON, default=dict)
    skills = Column(JSON, default=list)
    domains = Column(JSON, default=list)
    frameworks = Column(JSON, default=list)
    technologies = Column(JSON, default=list)
    project_technologies = Column(JSON, default=list)
    covered_topics = Column(JSON, default=list)
    weak_topics = Column(JSON, default=list)
    strong_topics = Column(JSON, default=list)
    difficulty = Column(String, default="medium")
    current_attempts = Column(Integer, default=0)
    current_answers = Column(JSON, default=list)
    current_expected_points = Column(JSON, default=list)
    question_number = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    retrieval_query = Column(Text, nullable=False)
    role = Column(String, nullable=False)
    difficulty = Column(String, default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="questions")
    retrieved_chunks = relationship("RetrievedChunk", back_populates="question", cascade="all, delete-orphan")


class RetrievedChunk(Base):
    __tablename__ = "retrieved_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False, index=True)
    source = Column(String, nullable=True)
    role = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    semantic_score = Column(Float, default=0)
    skill_overlap = Column(Float, default=0)
    role_relevance = Column(Float, default=0)
    final_score = Column(Float, default=0)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)

    question = relationship("InterviewQuestion", back_populates="retrieved_chunks")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=True, index=True)
    answer = Column(Text, nullable=False)
    classification = Column(String, nullable=False)
    feedback = Column(Text, nullable=False)
    adjustment = Column(String, default="maintain")
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="answers")
