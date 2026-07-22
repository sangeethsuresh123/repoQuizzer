from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Repo(Base):
    __tablename__ = "repos"

    id = Column(String(64), primary_key=True)
    url = Column(Text, nullable=False)
    cloned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_url = Column(Text, nullable=False)
    scope_path = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    quiz_json = Column(Text, nullable=False)
    answers_json = Column(Text, nullable=False)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
