from collections.abc import AsyncGenerator
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

class Base(DeclarativeBase):
    pass

class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Creating a database

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn: # this start the DB engine
        await conn.run_sync(Base.metadata.create_all) # This create all the tables.

# This will give us a session which will allow to access the DB and write and read from it asynchronously.
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# what is session in SQLAlchemy
"""
1. A Session is NOT just a connection.
- It is a transaction manager, unit of work tracker, cache, state machine.
- It keeps track of what objects were loaded, what objects were modified, what nees to be committed, what should be rolled back.

This means it holds mutable state.

- The problem of concurrency

If we share one global session:
- Objects are cached, Transaction state overlaps, One commit might include changes from the other req, Rollback from one request could undo the other's work.

Transaction in relational databases:
- Relational db's gurantees:
    - Atomicity
    - Isolation
    - Consistency
    But its only inside a transaction.

Each request usually represents : One logical business transaction.
- Transfer money, Create order, Update inventory, Create user + profile
These all should be isolated.

If request A fails -> It must rollback -> Without affecting request B.

=======================================================================

2. Why Primsa & Mongoose  Feels Simpler?

- You create one global client(connection pool is managed internally).
- Operations are atomic at the document level for mongoDB.

for mongoDB:
- If you need multi-document transactions, you explicitly start session/transaction - otherwise you don't manage per-request sessions manually.

for prisma:
- It uses a single global prismaclient instance -> like a shared engine
- Internally, it manages a connection pool for you.
- Each query runs in its own implicit transaction by default.
- Don't need to manually create "sessions" like in SQLAlchemy
- Prisma hides session management.

That's why we can safely resue one client globally.

============================================================================

Incoming request
    ↓
Create session
    ↓
Do work
    ↓
Commit OR rollback
    ↓
Close session (return connection to pool)

This gives -> Isolation, Safety, Clean memory, Proper connection reuse.

This gives:
- Isolation
- Safety
- Clean memory
- Proper connection reuse

** Each request must have:
    - Independent transaction -> So failures don't affect others
    - Idependent session -> Because session stores mutable state
    - To maintain database consistency.


"""