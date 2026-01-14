from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.commands import RemoveItemFromCart
from app.infrastructure.repositories.event_store import EventStore, ConcurrencyException
from app.infrastructure.repositories.read_model import ReadModelRepository


class RemoveItemFromCartUseCase:
    """
    Use Case: Usuń produkt z koszyka.
    
    Podobny flow jak AddItem, ale bez HTTP call do serwisu produktów.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)

    async def execute(self, command: RemoveItemFromCart, max_retries: int = 3) -> None:
        """Execute remove item command with retry on concurrency conflicts"""
        for attempt in range(max_retries):
            try:
                await self._execute_once(command)
                return
            except ConcurrencyException as e:
                if attempt == max_retries - 1:
                    raise
                continue

    async def _execute_once(self, command: RemoveItemFromCart) -> None:
        """Single execution attempt"""
        # Załaduj agregat
        aggregate = await self.event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            raise ValueError(f"Cart {command.cart_id} not found")

        # Wykonaj komendę
        aggregate.remove_item(product_id=command.product_id)

        # Zapisz eventy
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Zaktualizuj read model
        await self._update_read_model(aggregate)

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
