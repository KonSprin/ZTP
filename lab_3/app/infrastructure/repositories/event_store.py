from uuid import UUID
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.domain.cart.aggregate import CartAggregate
from app.domain.cart.events import (
    DomainEvent,
    CartCreated,
    ItemAddedToCart,
    ItemRemovedFromCart,
    ItemQuantityChanged,
    CartCheckedOut,
    CartExpired,
    ProductReserved,
    ProductReservationReleased,
)
from app.infrastructure.database import cart_events


class ConcurrencyException(Exception):
    """Raised when optimistic locking detects concurrent modification"""
    pass


class EventStore:
    """
    Event Store Repository - zapisuje i odczytuje eventy.
    
    Kluczowe dla event sourcingu:
    1. Append-only storage
    2. Optimistic locking przez aggregate_version (unique constraint)
    3. Deserializacja eventów z JSON
    """

    EVENT_TYPE_MAP = {
        "CartCreated": CartCreated,
        "ItemAddedToCart": ItemAddedToCart,
        "ItemRemovedFromCart": ItemRemovedFromCart,
        "ItemQuantityChanged": ItemQuantityChanged,
        "CartCheckedOut": CartCheckedOut,
        "CartExpired": CartExpired,
        "ProductReserved": ProductReserved,
        "ProductReservationReleased": ProductReservationReleased,
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_events(
        self, 
        aggregate_id: UUID, 
        events: list[DomainEvent], 
        expected_version: int
    ) -> None:
        """
        Save events to event store with optimistic locking.
        
        Optimistic locking:
        - Sprawdzamy czy ostatni event ma expected_version
        - Jeśli ktoś zapisał między czasem, unique constraint na (aggregate_id, version) 
          rzuci IntegrityError
        - To zapewnia że nie tracimy eventów przy concurrent writes
        
        Args:
            aggregate_id: ID agregatu
            events: Lista eventów do zapisania
            expected_version: Oczekiwana wersja agregatu (dla optimistic locking)
        
        Raises:
            ConcurrencyException: Jeśli wykryto równoczesną modyfikację
        """
        if not events:
            return

        # Sprawdź aktualną wersję w bazie
        current_version = await self._get_current_version(aggregate_id)
        
        if current_version != expected_version:
            raise ConcurrencyException(
                f"Concurrency conflict: expected version {expected_version}, "
                f"but current version is {current_version}"
            )

        # Zapisz wszystkie eventy w jednej transakcji
        try:
            for event in events:
                stmt = insert(cart_events).values(
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    aggregate_version=event.aggregate_version,
                    event_type=event.event_type,
                    event_data=event.to_dict(),
                    occurred_at=event.occurred_at,
                )
                await self.session.execute(stmt)
            
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            # Unique constraint violation na (aggregate_id, version)
            raise ConcurrencyException(
                f"Concurrency conflict detected when saving events: {str(e)}"
            ) from e

    async def get_events(self, aggregate_id: UUID) -> list[DomainEvent]:
        """
        Get all events for aggregate, ordered by version.
        Używane do odtworzenia stanu agregatu (replay).
        """
        stmt = (
            select(cart_events)
            .where(cart_events.c.aggregate_id == aggregate_id)
            .order_by(cart_events.c.aggregate_version.asc())
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

    async def load_aggregate(self, aggregate_id: UUID) -> CartAggregate | None:
        """
        Load aggregate by replaying all events.
        To jest serce event sourcingu - odtwarzamy stan z historii eventów.
        """
        events = await self.get_events(aggregate_id)
        
        if not events:
            return None

        aggregate = CartAggregate(aggregate_id)
        for event in events:
            # is_new=False bo to replay, nie dodajemy do uncommitted_events
            aggregate.apply_event(event, is_new=False)

        return aggregate

    async def _get_current_version(self, aggregate_id: UUID) -> int:
        """Get current version of aggregate from event store"""
        stmt = (
            select(cart_events.c.aggregate_version)
            .where(cart_events.c.aggregate_id == aggregate_id)
            .order_by(cart_events.c.aggregate_version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        return row[0] if row else 0
