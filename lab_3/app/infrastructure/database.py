from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    JSON,
    Index,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime


metadata = MetaData()

# Event Store - główna tabela dla event sourcingu
# Wszystkie eventy są tu zapisywane i odtwarzamy z nich stan
cart_events = Table(
    "cart_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_id", UUID, unique=True, nullable=False),
    Column("aggregate_id", UUID, nullable=False, index=True),
    Column("aggregate_version", Integer, nullable=False),
    Column("event_type", String(100), nullable=False),
    Column("event_data", JSON, nullable=False),
    Column("occurred_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    # Unique constraint zapewnia spójność - jeden version na aggregate
    # To jest kluczowe dla optimistic locking
    Index("idx_aggregate_version", "aggregate_id", "aggregate_version", unique=True),
    Index("idx_occurred_at", "occurred_at"),
)

# Read Model - zdenormalizowana projekcja dla szybkich odczytów
# Aktualizowana asynchronicznie po zapisaniu eventów
cart_read_model = Table(
    "cart_read_model",
    metadata,
    Column("cart_id", UUID, primary_key=True),
    Column("user_id", String(255), nullable=False, index=True),
    Column("status", String(50), nullable=False),
    Column("items", JSON, nullable=False, default=list),  # [{product_id, name, price, quantity}]
    Column("total_amount", Float, nullable=False, default=0.0),
    Column("item_count", Integer, nullable=False, default=0),
    Column("version", Integer, nullable=False, default=0),
    Column("created_at", DateTime, nullable=False),
    Column("last_activity", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
    Index("idx_user_status", "user_id", "status"),
    Index("idx_last_activity", "last_activity"),
)


class Database:
    """Database connection manager"""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            echo=True,
            pool_size=20,
            max_overflow=0,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all tables in database"""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables (for testing)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        async with self.session_factory() as session:
            yield session

    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()
