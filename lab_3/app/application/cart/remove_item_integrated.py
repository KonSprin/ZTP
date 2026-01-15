from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.commands import RemoveItemFromCart
from app.domain.product.commands import ReleaseReservation
from app.infrastructure.repositories.event_store import EventStore, ConcurrencyException
from app.infrastructure.repositories.read_model import ReadModelRepository
from app.application.product.reserve_stock import ReleaseReservationUseCase


class RemoveItemFromCartIntegratedUseCase:
    """
    Use Case: Remove item from cart AND release stock reservation.
    
    This ensures that when item is removed, the stock reservation
    is also released back to the product inventory.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)
        self.release_reservation_use_case = ReleaseReservationUseCase(session)

    async def execute(self, command: RemoveItemFromCart, max_retries: int = 3) -> None:
        """Execute remove item command with stock reservation release"""
        for attempt in range(max_retries):
            try:
                await self._execute_once(command)
                return
            except ConcurrencyException:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: RemoveItemFromCart) -> None:
        """Single execution attempt"""
        # Load cart aggregate
        aggregate = await self.event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            raise ValueError(f"Cart {command.cart_id} not found")

        # Check if product exists in cart (need quantity for release)
        if command.product_id not in aggregate.items:
            raise ValueError(f"Product {command.product_id} not found in cart")

        product_id = command.product_id

        # Remove item from cart
        aggregate.remove_item(product_id=command.product_id)

        # Save cart events
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Update cart read model
        await self._update_read_model(aggregate)

        # Release product reservation
        try:
            release_command = ReleaseReservation(
                product_id=product_id,
                cart_id=command.cart_id,
                reason="item_removed"
            )
            await self.release_reservation_use_case.execute(release_command)
        except Exception as e:
            print(f"Warning: Failed to release reservation for {product_id}: {e}")

    async def _update_read_model(self, aggregate) -> None:
        """Update read model projection"""
        items = [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "price": item.price,
                "quantity": item.quantity,
                "total_price": item.total_price,
            }
            for item in aggregate.items.values()
        ]

        await self.read_model_repo.update_projection(
            cart_id=aggregate.cart_id,
            status=aggregate.status,
            items=items,
            total_amount=aggregate.total_amount,
            item_count=aggregate.item_count,
            version=aggregate.version,
            last_activity=aggregate.last_activity,
        )
