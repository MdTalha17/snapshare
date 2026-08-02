from collections.abc import AsyncGenerator
import uuid
from fastapi import Depends
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTableUUID, Base):
    posts = relationship("Post", back_populates="user")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="posts")
    

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite's create_all does not evolve existing tables. Earlier local
        # databases used a posts table without ownership information, so add
        # and backfill the column once rather than requiring users to discard
        # their existing feed data.
        post_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("posts")}
        )
        if "user_id" not in post_columns:
            await conn.execute(text("ALTER TABLE posts ADD COLUMN user_id UUID"))
            await conn.execute(text("""
                UPDATE posts
                SET user_id = (SELECT id FROM user ORDER BY id LIMIT 1)
                WHERE user_id IS NULL
            """))
        
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
        
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)