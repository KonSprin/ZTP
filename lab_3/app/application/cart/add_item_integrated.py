from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.commands import AddItemToCart
from app.domain.product.commands import ReserveStock, ReleaseReservation
from app.infrastructure.repositories.event_store import EventStore, ConcurrencyException
from app.infrastructure.repositories.read_model import ReadModelRepository
from app.infrastructure.repositories.product_read_model import ProductReadModelRepository
from app.application.product.reserve_stock import ReserveStockUseCase, ReleaseReservationUseCase


class ProductNotFoundError(Exception):
    """Raised when product doesn't exist in product service"""
    pass


class AddItemToCartIntegratedUseCase:
    """
    Use Case: Add item to cart WITH stock reservation.
    
    This is the integrated version that:
    1. Fetches product from read model
    2. Reserves stock in product domain
    3. Adds item to cart
    4. If cart operation fails, releases reservation
    
    This ensures products are reserved when added to cart.
    """

    def __init__(self, session: AsyncSession):
        self.cart_event_store = EventStore(session)
        self.cart_read_model_repo = ReadModelRepository(session)
        self.product_read_model_repo = ProductReadModelRepository(session)
        self.reserve_stock_use_case = ReserveStockUseCase(session)
        self.release_reservation_use_case = ReleaseReservationUseCase(session)

    async def execute(self, command: AddItemToCart, max_retries: int = 3) -> None:
        """
        Execute add item to cart command with stock reservation.
        
        Args:
            command: AddItemToCart command
            max_retries: Max retries for concurrency conflicts
        
        Raises:
            ProductNotFoundError: If product doesn't exist
            ValueError: If cart doesn't exist or insufficient stock
            ConcurrencyException: If failed after max_retries
        """
        # 1. Fetch product from read model
        product = await self.product_read_model_repo.get_product(command.product_id)
        if product is None:
            raise ProductNotFoundError(f"Product {command.product_id} not found")

        # 2. Reserve stock first
        try:
            reserve_command = ReserveStock(
                product_id=command.product_id,
                cart_id=command.cart_id,
                quantity=command.quantity
            )
            await self.reserve_stock_use_case.execute(reserve_command)
        except ValueError as e:
            # Insufficient stock or other validation error
            raise ValueError(f"Cannot reserve stock: {str(e)}")

        # 3. Try to add item to cart
        try:
            for attempt in range(max_retries):
                try:
                    await self._execute_cart_operation(command, product)
                    return  # Success!
                except ConcurrencyException:
                    if attempt == max_retries - 1:
                        raise
                    continue
        except Exception as e:
            # Cart operation failed - release the reservation
            await self._rollback_reservation(command)
            raise

    async def _execute_cart_operation(self, command: AddItemToCart, product) -> None:
        """Execute cart operation (add item)"""
        # Load cart aggregate
        aggregate = await self.cart_event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            raise ValueError(f"Cart {command.cart_id} not found")

        # Execute command
        aggregate.add_item(
            product_id=command.product_id,
            product_name=product.name,
            price=product.price,
            quantity=command.quantity,
        )

        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.cart_event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Update read model
        await self._update_cart_read_model(aggregate)

    async def _update_cart_read_model(self, aggregate) -> None:
        """Update cart read model projection"""
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

        await self.cart_read_model_repo.update_projection(
            cart_id=aggregate.cart_id,
            status=aggregate.status,
            items=items,
            total_amount=aggregate.total_amount,
            item_count=aggregate.item_count,
            version=aggregate.version,
            last_activity=aggregate.last_activity,
        )

    async def _rollback_reservation(self, command: AddItemToCart) -> None:
        """Rollback stock reservation if cart operation fails"""
        try:
            release_command = ReleaseReservation(
                product_id=command.product_id,
                cart_id=command.cart_id,
                reason="cart_operation_failed"
            )
            await self.release_reservation_use_case.execute(release_command)
        except Exception as e:
            # Log error but don't fail - we already have a primary error
            print(f"Warning: Failed to release reservation during rollback: {e}")
