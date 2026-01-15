import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.commands import ExpireCart
from app.domain.product.commands import ReleaseReservation
from app.infrastructure.repositories.event_store import EventStore
from app.infrastructure.repositories.read_model import ReadModelRepository
from app.application.product.reserve_stock import ReleaseReservationUseCase


class ExpireCartUseCase:
    """
    Use Case: Expire a cart and release all product reservations.
    
    Called by the background task when cart is inactive for 15 minutes.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)
        self.release_reservation_use_case = ReleaseReservationUseCase(session)

    async def execute(self, command: ExpireCart) -> None:
        """
        Execute expire cart command.
        
        Steps:
        1. Load cart aggregate
        2. Get all products in cart
        3. Expire cart (generates CartExpired event)
        4. Release all product reservations
        5. Update read model
        """
        # Load cart aggregate
        aggregate = await self.event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            # Already deleted or doesn't exist
            return
        
        if aggregate.status != "PENDING":
            # Already checked out or expired
            return

        # Get products to release
        products_to_release = [
            (item.product_id, item.quantity) 
            for item in aggregate.items.values()
        ]

        # Expire cart
        aggregate.expire(reason=command.reason)

        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Update read model
        await self._update_read_model(aggregate)

        # Release all product reservations
        for product_id, quantity in products_to_release:
            try:
                release_command = ReleaseReservation(
                    product_id=product_id,
                    cart_id=command.cart_id,
                    reason="cart_expired"
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


class CartExpirationBackgroundTask:
    """
    Background task that periodically checks for expired carts.
    
    Runs every 1 minute and expires carts inactive for 15+ minutes.
    """

    def __init__(self, db_factory, interval_seconds: int = 60, timeout_minutes: int = 15):
        self.db_factory = db_factory
        self.interval_seconds = interval_seconds
        self.timeout_minutes = timeout_minutes
        self._task = None
        self._running = False

    async def start(self) -> None:
        """Start the background task"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        print(f"Cart expiration task started (check interval: {self.interval_seconds}s, timeout: {self.timeout_minutes}m)")

    async def stop(self) -> None:
        """Stop the background task"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("Cart expiration task stopped")

    async def _run(self) -> None:
        """Main task loop"""
        while self._running:
            try:
                await self._check_and_expire_carts()
            except Exception as e:
                print(f"Error in cart expiration task: {e}")
            
            await asyncio.sleep(self.interval_seconds)

    async def _check_and_expire_carts(self) -> None:
        """Check for expired carts and expire them"""
        async for session in self.db_factory():
            try:
                # Get expired cart IDs from read model
                read_model_repo = ReadModelRepository(session)
                expired_cart_ids = await read_model_repo.get_expired_carts(
                    timeout_minutes=self.timeout_minutes
                )

                if not expired_cart_ids:
                    return

                print(f"Found {len(expired_cart_ids)} expired carts")

                # Expire each cart
                for cart_id in expired_cart_ids:
                    try:
                        command = ExpireCart(
                            cart_id=cart_id,
                            reason=f"{self.timeout_minutes}_minute_timeout"
                        )
                        
                        use_case = ExpireCartUseCase(session)
                        await use_case.execute(command)
                        print(f"Expired cart: {cart_id}")
                    except Exception as e:
                        print(f"Failed to expire cart {cart_id}: {e}")

            except Exception as e:
                print(f"Error checking expired carts: {e}")
            finally:
                await session.close()
