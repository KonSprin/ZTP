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
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone


metadata_products = MetaData()

# Product Event Store
product_events = Table(
    "product_events",
    metadata_products,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_id", UUID, unique=True, nullable=False),
    Column("aggregate_id", String(255), nullable=False, index=True),
    Column("aggregate_version", Integer, nullable=False),
    Column("event_type", String(100), nullable=False),
    Column("event_data", JSON, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    # Optimistic locking
    Index("idx_product_aggregate_version", "aggregate_id", "aggregate_version", unique=True),
    Index("idx_product_occurred_at", "occurred_at"),
)

# Product Read Model
product_read_model = Table(
    "product_read_model",
    metadata_products,
    Column("product_id", String(255), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("price", Float, nullable=False),
    Column("description", String(1000), nullable=False, default=""),
    Column("total_stock", Integer, nullable=False, default=0),
    Column("reserved_stock", Integer, nullable=False, default=0),
    Column("available_stock", Integer, nullable=False, default=0),
    Column("version", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)),
    Index("idx_product_available", "available_stock"),
)


class ProductDatabase:
    """Database connection manager for products service"""

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
            await conn.run_sync(metadata_products.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables (for testing)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata_products.drop_all)

    async def get_session(self) -> AsyncSession: # type: ignore
        """Get database session"""
        async with self.session_factory() as session:
            yield session # type: ignore

    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()
