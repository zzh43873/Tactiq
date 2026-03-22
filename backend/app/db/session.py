"""
数据库会话管理
支持 SQLite (aiosqlite) 和 PostgreSQL (asyncpg)
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker

from app.config import settings


# 数据库URL，支持 SQLite 和 PostgreSQL
DATABASE_URL = settings.DATABASE_URL
# 如果使用 SQLite，确保使用 aiosqlite 驱动
if DATABASE_URL.startswith("sqlite:") and not DATABASE_URL.startswith("sqlite+aiosqlite:"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:", "sqlite+aiosqlite:", 1)

# 创建异步引擎
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # 调试模式下打印SQL
    pool_pre_ping=True,   # 连接池健康检查
    # SQLite 不需要连接池配置
    **({"pool_size": 10, "max_overflow": 20} if "postgresql" in DATABASE_URL else {})
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖函数
    
    使用方式：
    ```python
    @router.get("/items")
    async def get_items(db: AsyncSession = Depends(get_db)):
        ...
    ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库
    创建所有表
    """
    from app.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
