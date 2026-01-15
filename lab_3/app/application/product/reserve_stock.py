from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.product.commands import ReserveStock, ReleaseReservation, CheckoutReservation
from app.infrastructure.repositories.product_event_store import (
    ProductEventStore,
    ConcurrencyException
)
from app.infrastructure.repositories.product_read_model import ProductReadModelRepository


class ReserveStockUseCase:
    """
    Use Case: Reserve stock for a cart.
    
    Called when item is added to cart.
    Implements retry for concurrency conflicts.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = ProductEventStore(session)
        self.read_model_repo = ProductReadModelRepository(session)

    async def execute(self, command: ReserveStock, max_retries: int = 3) -> None:
        """Execute reserve stock command with retry"""
        for attempt in range(max_retries):
            try:
                await self._execute_once(command)
                return
            except ConcurrencyException:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: ReserveStock) -> None:
        """Single execution attempt"""
        # Load aggregate
        aggregate = await self.event_store.load_aggregate(command.product_id)
        
        if aggregate is None:
            raise ValueError(f"Product {command.product_id} not found")

        # Execute command
        aggregate.reserve_stock(
            cart_id=command.cart_id,
            quantity=command.quantity
        )

        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.product_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Update read model
        await self._update_read_model(aggregate)

    async def _update_read_model(self, aggregate) -> None:
        """Update read model projection"""
        await self.read_model_repo.update_projection(
            product_id=aggregate.product_id,
            name=aggregate.name,
            price=aggregate.price,
            description=aggregate.description,
            total_stock=aggregate.total_stock,
            reserved_stock=aggregate.reserved_stock,
            available_stock=aggregate.available_stock,
            version=aggregate.version,
        )


class ReleaseReservationUseCase:
    """
    Use Case: Release stock reservation.
    
    Called when:
    - Item is removed from cart
    - Cart expires
    - Reservation times out
    """

    def __init__(self, session: AsyncSession):
        self.event_store = ProductEventStore(session)
        self.read_model_repo = ProductReadModelRepository(session)

    async def execute(self, command: ReleaseReservation, max_retries: int = 3) -> None:
        """Execute release reservation command with retry"""
        for attempt in range(max_retries):
            try:
                await self._execute_once(command)
                return
            except ConcurrencyException:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: ReleaseReservation) -> None:
        """Single execution attempt"""
        # Load aggregate
        aggregate = await self.event_store.load_aggregate(command.product_id)
        
        if aggregate is None:
            raise ValueError(f"Product {command.product_id} not found")

        # Execute command
        aggregate.release_reservation(
            cart_id=command.cart_id,
            reason=command.reason
        )

        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        if uncommitted_events:  # May be empty if no reservation existed
            await self.event_store.save_events(
                aggregate_id=command.product_id,
                events=uncommitted_events,
                expected_version=aggregate.version - len(uncommitted_events),
            )

            # Update read model
            await self._update_read_model(aggregate)

    async def _update_read_model(self, aggregate) -> None:
        """Update read model projection"""
        await self.read_model_repo.update_projection(
            product_id=aggregate.product_id,
            name=aggregate.name,
            price=aggregate.price,
            description=aggregate.description,
            total_stock=aggregate.total_stock,
            reserved_stock=aggregate.reserved_stock,
            available_stock=aggregate.available_stock,
            version=aggregate.version,
        )


class CheckoutReservationUseCase:
    """
    Use Case: Complete checkout - release reservation and decrease stock.
    
    Called when cart is successfully checked out.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = ProductEventStore(session)
        self.read_model_repo = ProductReadModelRepository(session)

    async def execute(self, command: CheckoutReservation, max_retries: int = 3) -> None:
        """Execute checkout reservation command with retry"""
        for attempt in range(max_retries):
            try:
                await self._execute_once(command)
                return
            except ConcurrencyException:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: CheckoutReservation) -> None:
        """Single execution attempt"""
        # Load aggregate
        aggregate = await self.event_store.load_aggregate(command.product_id)
        
        if aggregate is None:
            raise ValueError(f"Product {command.product_id} not found")

        # Execute command
        aggregate.checkout_reservation(
            cart_id=command.cart_id,
            order_id=command.order_id
        )

        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.product_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Update read model
        await self._update_read_model(aggregate)

    async def _update_read_model(self, aggregate) -> None:
        """Update read model projection"""
        await self.read_model_repo.update_projection(
            product_id=aggregate.product_id,
            name=aggregate.name,
            price=aggregate.price,
            description=aggregate.description,
            total_stock=aggregate.total_stock,
            reserved_stock=aggregate.reserved_stock,
            available_stock=aggregate.available_stock,
            version=aggregate.version,
        )
