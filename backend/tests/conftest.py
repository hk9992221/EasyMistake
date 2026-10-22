import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

for key, value in {
    'DATABASE_URL': os.environ.get('TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:'),
    'DATABASE_URL_SYNC': 'sqlite:///:memory:',
    'SECRET_KEY': 'test-only-secret-not-for-production',
    'S3_ENDPOINT': 'http://localhost:9000', 'S3_ACCESS_KEY': 'test',
    'S3_SECRET_KEY': 'test', 'S3_BUCKET': 'test', 'OPENAI_API_KEY': 'test',
    'EXPORT_WORKER_AUTO_START': 'false',
}.items():
    os.environ.setdefault(key, value)

from api.models import Base, User
from api.main import app
from api.core.database import get_db
from api.core.deps import get_current_user


@compiles(JSONB, 'sqlite')
def sqlite_jsonb(type_, compiler, **kwargs):
    return 'JSON'


@pytest.fixture
async def db():
    engine = create_async_engine(os.environ.get('TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:'))
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine.sync_engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    async with engine.connect() as connection:
        transaction = await connection.begin()
        if engine.dialect.name == 'postgresql':
            schema = 'test_' + uuid4().hex
            await connection.exec_driver_sql(f'CREATE SCHEMA {schema}')
            await connection.exec_driver_sql(f'SET LOCAL search_path TO {schema}')
        await connection.run_sync(Base.metadata.create_all)
        async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def users(db):
    owner = User(email='owner@example.com', password_hash='unused')
    other = User(email='other@example.com', password_hash='unused')
    db.add_all([owner, other])
    await db.commit()
    return owner, other


@pytest.fixture
async def client(db, users):
    async def override_db():
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: users[0]
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client
    app.dependency_overrides.clear()
