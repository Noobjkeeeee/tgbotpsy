import datetime
import os
from datetime import timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "bot_data.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    username = Column(String(100), nullable=True)
    request_type = Column(String(50))
    name = Column(String(100))
    phone = Column(String(20))
    description = Column(Text)
    email = Column(String(100))
    tg_account = Column(String(100))
    status = Column(String(20), default="новая")
    admin_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(timezone.utc),
        onupdate=lambda: datetime.datetime.now(timezone.utc),
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    question_text = Column(Text, nullable=False)
    admin_message_id = Column(Integer, nullable=True)
    admin_messages = Column(JSON, nullable=True, default=[])
    status = Column(String(20), default="ожидает")
    answer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    answered_at = Column(DateTime, nullable=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_next_question_id():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.max(Question.id)))
        max_id = result.scalar()
        return (max_id or 0) + 1


async def create_question(
    user_id: int, question_text: str, admin_message_id: int = None
):
    async with AsyncSessionLocal() as session:
        question = Question(
            user_id=user_id,
            question_text=question_text,
            admin_message_id=admin_message_id,
            status="ожидает",
        )
        session.add(question)
        await session.commit()
        await session.refresh(question)
        return question.id


async def get_question_by_id(question_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()


async def get_question_by_admin_message(admin_message_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Question).where(Question.admin_message_id == admin_message_id)
        )
        return result.scalar_one_or_none()


async def update_question_answer(question_id: int, answer_text: str, status: str = "отвечен"):
    async with AsyncSessionLocal() as session:
        question = await session.get(Question, question_id)
        if question:
            question.answer_text = answer_text
            question.status = status
            await session.commit()


async def get_pending_questions_count():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Question.id)).where(Question.status == "ожидает")
        )
        return result.scalar()


async def get_application_by_id(app_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application).where(Application.id == app_id)
        )
        return result.scalar_one_or_none()


async def update_application_status(
    app_id: int, status: str, admin_comment: str = None
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application).where(Application.id == app_id)
        )
        app = result.scalar_one_or_none()
        if app:
            app.status = status
            if admin_comment:
                app.admin_comment = admin_comment
            await session.commit()
            return True
        return False
