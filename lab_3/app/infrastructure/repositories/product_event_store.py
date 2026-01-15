from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.domain.product.aggregate import ProductAggregate
from app.domain.product.events import (
    DomainEvent,
    ProductCreated,
    ProductStockReserved,
    ProductStockReservationReleased,
    ProductStockIncreased,
    ProductStockDecreased,
    ProductPriceChanged,
    ProductUpdated,
)
from app.infrastructure.database_products import product_events


class ConcurrencyException(Exception):
    """Raised when optimistic locking detects concurrent modification"""
    pass


class ProductEventStore:
    """
    Event Store for Product domain.
    
    Same pattern as cart event store but for products.
    """

    EVENT_TYPE_MAP = {
        "ProductCreated": ProductCreated,
        "ProductStockReserved": ProductStockReserved,
        "ProductStockReservationReleased": ProductStockReservationReleased,
        "ProductStockIncreased": ProductStockIncreased,
        "ProductStockDecreased": ProductStockDecreased,
        "ProductPriceChanged": ProductPriceChanged,
        "ProductUpdated": ProductUpdated,
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_events(
        self, 
        aggregate_id: str, 
        events: list[DomainEvent], 
        expected_version: int
    ) -> None:
        """
        Save events to event store with optimistic locking.
        
        Args:
            aggregate_id: Product ID
            events: List of events to save
            expected_version: Expected version for optimistic locking
        
        Raises:
            ConcurrencyException: If concurrent modification detected
        """
        if not events:
            return

        # Check current version
        current_version = await self._get_current_version(aggregate_id)
        
        if current_version != expected_version:
            raise ConcurrencyException(
                f"Concurrency conflict: expected version {expected_version}, "
                f"but current version is {current_version}"
            )

        # Save all events in one transaction
        try:
            for event in events:
                occured_at = event.occurred_at
                # if not occured_at.tzinfo:
                #     occured_at = occured_at.replace(tzinfo=None)

                stmt = insert(product_events).values(
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    aggregate_version=event.aggregate_version,
                    event_type=event.event_type,
                    event_data=event.to_dict(),
                    occurred_at=occured_at,
                )
                await self.session.execute(stmt)
            
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise ConcurrencyException(
                f"Concurrency conflict detected when saving events: {str(e)}"
            ) from e

    async def get_events(self, aggregate_id: str) -> list[DomainEvent]:
        """Get all events for aggregate, ordered by version"""
        stmt = (
            select(product_events)
            .where(product_events.c.aggregate_id == aggregate_id)
            .order_by(product_events.c.aggregate_version.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        events = []
        for row in rows:
            event_class = self.EVENT_TYPE_MAP.get(row.event_type)
            if event_class is None:
                raise ValueError(f"Unknown event type: {row.event_type}")
            
            event = event_class(**row.event_data)
            events.append(event)

        return events

    async def load_aggregate(self, aggregate_id: str) -> ProductAggregate | None:
        """Load aggregate by replaying all events"""
        events = await self.get_events(aggregate_id)
        
        if not events:
            return None

        aggregate = ProductAggregate(aggregate_id)
        for event in events:
            aggregate.apply_event(event, is_new=False)

        return aggregate

    async def _get_current_version(self, aggregate_id: str) -> int:
        """Get current version of aggregate from event store"""
        stmt = (
            select(product_events.c.aggregate_version)
            .where(product_events.c.aggregate_id == aggregate_id)
            .order_by(product_events.c.aggregate_version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        return row[0] if row else 0
