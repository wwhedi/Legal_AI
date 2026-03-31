from __future__ import annotations

import os
from functools import lru_cache
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

POSTGRES_DSN_ENV = "POSTGRES_DSN"
DEFAULT_POSTGRES_DSN = "postgresql+asyncpg://user:password@localhost:5432/legal_ai"


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    """
    创建全局复用的 AsyncEngine。

    注意：
    - 所有数据库 I/O 必须通过 async Session 完成，遵守项目的 async/await 规范。
    - 具体的表模型与 CRUD 逻辑将在后续阶段补充。
    """

    dsn = os.getenv(POSTGRES_DSN_ENV, DEFAULT_POSTGRES_DSN)
    return create_async_engine(
        dsn,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI 依赖中使用的 Session 提供器示例：

    async def some_endpoint(session: AsyncSession = Depends(get_db_session)):
        ...
    """

    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        yield session


__all__ = [
    "get_async_engine",
    "get_async_sessionmaker",
    "get_db_session",
]

