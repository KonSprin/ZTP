from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.domain.cart.commands import AddItemToCart
from app.infrastructure.repositories.event_store import EventStore, ConcurrencyException
from app.infrastructure.repositories.read_model import ReadModelRepository


class ProductNotFoundError(Exception):
    """Raised when product doesn't exist in product service"""
    pass


class AddItemToCartUseCase:
    """
    Use Case: Dodaj produkt do koszyka.
    
    Flow:
    1. Pobierz informacje o produkcie z serwisu produktowego (HTTP)
    2. Załaduj agregat z event store (replay eventów)
    3. Wykonaj komendę add_item (walidacja biznesowa w agregacie)
    4. Zapisz nowe eventy z optimistic locking
    5. Zaktualizuj read model
    
    Retry w przypadku ConcurrencyException (optimistic locking conflict).
    """

    def __init__(self, session: AsyncSession, products_service_url: str):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)
        self.products_service_url = products_service_url

    async def execute(self, command: AddItemToCart, max_retries: int = 3) -> None:
        """
        Execute add item to cart command with retry on concurrency conflicts.
        
        Args:
            command: AddItemToCart command
            max_retries: Maksymalna liczba prób w przypadku konfliktu współbieżności
        
        Raises:
            ProductNotFoundError: Jeśli produkt nie istnieje
            ValueError: Jeśli koszyk nie istnieje lub jest w złym stanie
            ConcurrencyException: Jeśli nie udało się zapisać po max_retries
        """
        # Pobierz dane produktu z serwisu produktowego
        product = await self._fetch_product(command.product_id)

        # Retry loop dla optimistic locking
        for attempt in range(max_retries):
            try:
                await self._execute_once(command, product)
                return  # Sukces, wychodzimy
            except ConcurrencyException as e:
                if attempt == max_retries - 1:
                    # Ostatnia próba, rzuć wyjątek
                    raise
                # Retry - załaduj najnowszy stan i spróbuj ponownie
                continue

    async def _execute_once(self, command: AddItemToCart, product: dict) -> None:
        """Single execution attempt"""
        # Załaduj agregat (replay eventów)
        aggregate = await self.event_store.load_aggregate(command.cart_id)
        
        if aggregate is None:
            raise ValueError(f"Cart {command.cart_id} not found")

        # Wykonaj komendę (biznesowa walidacja w agregacie)
        aggregate.add_item(
            product_id=command.product_id,
            product_name=product["name"],
            price=product["price"],
            quantity=command.quantity,
        )

        # Zapisz eventy (optimistic locking)
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events),
        )

        # Zaktualizuj read model
        await self._update_read_model(aggregate)

    async def _fetch_product(self, product_id: str) -> dict:
        """
        Fetch product from products service via HTTP.
        
        Returns:
            dict: {id, name, price, stock}
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.products_service_url}/products/{product_id}",
                    timeout=5.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ProductNotFoundError(f"Product {product_id} not found")
                raise
            except httpx.RequestError as e:
                raise Exception(f"Failed to fetch product: {str(e)}")

    async def _update_read_model(self, aggregate) -> None:
        """Update read model projection from aggregate state"""
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
