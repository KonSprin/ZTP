from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.commands import CheckoutCart
from app.infrastructure.repositories.event_store import EventStore, ConcurrencyException
from app.infrastructure.repositories.read_model import ReadModelRepository


class CheckoutCartUseCase:
    """
    Use Case: Finalizuj koszyk i utwórz zamówienie.
    
    Flow:
    1. Załaduj agregat
    2. Wykonaj checkout (generuje CartCheckedOut event)
    3. Zapisz eventy
    4. Zaktualizuj read model
    5. (Opcjonalnie) Wyślij event do domeny zamówień
    
    W przyszłości możesz dodać:
    - Publikację eventu CartCheckedOut do message brokera (RabbitMQ/Kafka)
    - Domenę zamówień nasłuchującą na ten event
    """

    def __init__(self, session: AsyncSession):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)

    async def execute(self, command: CheckoutCart, max_retries: int = 3) -> dict:
        """
        Execute checkout command.
        
        Returns:
            dict: {order_id, cart_id, total_amount}
        """
        for attempt in range(max_retries):
            try:
                return await self._execute_once(command)
            except ConcurrencyException as e:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: CheckoutCart) -> dict:
        """Single execution attempt"""
        # Załaduj agregat
        aggregate = await self.event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            raise ValueError(f"Cart {command.cart_id} not found")

        # Wykonaj checkout
        aggregate.checkout(order_id=command.order_id)

        # Zapisz eventy
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Zaktualizuj read model
        await self._update_read_model(aggregate)

        # TODO: Publish CartCheckedOut event to message broker
        # await self.event_publisher.publish(uncommitted_events[-1])

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
