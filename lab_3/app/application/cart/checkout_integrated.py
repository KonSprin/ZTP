from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.commands import CheckoutCart
from app.domain.product.commands import CheckoutReservation
from app.infrastructure.repositories.event_store import EventStore, ConcurrencyException
from app.infrastructure.repositories.read_model import ReadModelRepository
from app.application.product.reserve_stock import CheckoutReservationUseCase


class CheckoutCartIntegratedUseCase:
    """
    Use Case: Checkout cart AND complete product reservations.
    
    This finalizes the cart and:
    1. Releases reservations
    2. Decreases actual product stock
    3. Creates CartCheckedOut event
    
    This is a coordinated operation across cart and product domains.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)
        self.checkout_reservation_use_case = CheckoutReservationUseCase(session)

    async def execute(self, command: CheckoutCart, max_retries: int = 3):
        """Execute checkout command with product reservation completion"""
        for attempt in range(max_retries):
            try:
                return await self._execute_once(command)
            except ConcurrencyException:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: CheckoutCart) -> dict:
        """Single execution attempt"""
        # Load cart aggregate
        aggregate = await self.event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            raise ValueError(f"Cart {command.cart_id} not found")

        # Get products to checkout
        products_to_checkout = [
            (item.product_id, item.quantity) 
            for item in aggregate.items.values()
        ]

        # Checkout cart
        aggregate.checkout(order_id=command.order_id)

        # Save cart events
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Update cart read model
        await self._update_read_model(aggregate)

        # Complete all product reservations (release + decrease stock)
        for product_id, quantity in products_to_checkout:
            try:
                checkout_command = CheckoutReservation(
                    product_id=product_id,
                    cart_id=command.cart_id,
                    order_id=command.order_id
                )
                await self.checkout_reservation_use_case.execute(checkout_command)
            except Exception as e:
                # Log error but don't fail checkout
                # In production, this should trigger compensation logic
                print(f"Warning: Failed to checkout reservation for {product_id}: {e}")

        return {
            "order_id": command.order_id,
            "cart_id": command.cart_id,
            "total_amount": aggregate.total_amount,
        }

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
