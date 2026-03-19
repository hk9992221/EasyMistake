from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from api.core.config import settings
from api.models.base import Base


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
