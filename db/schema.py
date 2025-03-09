from sqlalchemy import Column, Integer, String, Text, ForeignKey, BLOB, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
import sys
import os
from pydantic import BaseModel

# 获取当前脚本的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 获取父级目录
parent_dir = os.path.dirname(current_dir)

# 将父级目录添加到 sys.path
sys.path.append(parent_dir)
from db.index import Base, engine

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(36), unique=True, index=True)
    password_hash = Column(String(255))
    nickname = Column(String(255), nullable=True)
    avatar_data = Column(String(255), nullable=True)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, index=True)  # 为 String 类型指定长度
    history = relationship("History", back_populates="session")
    evaluations = relationship("Evaluation", back_populates="session")

# 会话历史模型
class History(Base):
    __tablename__ = "histories"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"))  # 同样为此处的 String 类型指定长度
    user_input = Column(Text)
    model_response = Column(Text)
    session = relationship("Session", back_populates="history")


class OcrHistory(Base):
    __tablename__ = "ocr_histories"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(Text)
    wrong_place = Column(Text)
    response = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
# 评价模型
class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"))
    score: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[str] = mapped_column(Text)

    session = relationship("Session", back_populates="evaluations")

class HistoryResponse(BaseModel):
    id: int
    session_id: str
    user_input: str
    model_response: str

    class Config:
        orm_mode = True


class HistoryListResponse(BaseModel):
    histories: List[HistoryResponse]

class EvaluationData(BaseModel):
    session_id: str
    score: int  # 评价分数，如1到5
    feedback: str  # 用户的文字反馈


Base.metadata.create_all(bind=engine)
