from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Repo(Base):
    __tablename__ = "repos"

    id = Column(String(64), primary_key=True)  # slug from _slug_for_url
    url = Column(Text, nullable=False)
    cloned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks = relationship("RepoChunk", back_populates="repo", cascade="all, delete-orphan")


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


class RepoChunk(Base):
    __tablename__ = "repo_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(String(64), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding_id = Column(Text, nullable=False)  # ID in Chroma collection

    repo = relationship("Repo", back_populates="chunks")
