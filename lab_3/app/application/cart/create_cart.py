from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.cart.aggregate import CartAggregate
from app.domain.cart.commands import CreateCart
from app.infrastructure.repositories.event_store import EventStore
from app.infrastructure.repositories.read_model import ReadModelRepository


class CreateCartUseCase:
    """
    Use Case: Utwórz nowy koszyk zakupowy.
    
    Flow:
    1. Walidacja komendy
    2. Utworzenie nowego agregatu
    3. Wykonanie command na agregacie (generuje eventy)
    4. Zapisanie eventów do event store
    5. Aktualizacja read model
    
    Ten use case jest łatwo testowalny - możemy mockować repozytoria.
    """

    def __init__(self, session: AsyncSession):
        self.event_store = EventStore(session)
        self.read_model_repo = ReadModelRepository(session)

    async def execute(self, command: CreateCart) -> UUID:
        """
        Execute create cart command.
        
        Returns:
            cart_id: ID utworzonego koszyka
        """
        # Sprawdź czy koszyk już istnieje
        existing = await self.event_store.load_aggregate(command.cart_id)
        if existing is not None:
            raise ValueError(f"Cart {command.cart_id} already exists")

        # Utwórz nowy agregat i wykonaj komendę
        aggregate = CartAggregate(command.cart_id)
        aggregate.create(user_id=command.user_id)

        # Zapisz eventy (optimistic locking - expected_version=0 dla nowego)
        uncommitted_events = aggregate.get_uncommitted_events()
        await self.event_store.save_events(
            aggregate_id=command.cart_id,
            events=uncommitted_events,
            expected_version=0,
        )

        # Zaktualizuj read model
        await self.read_model_repo.create_projection(
            cart_id=command.cart_id,
            user_id=command.user_id,
            created_at=aggregate.created_at,
        )

        return command.cart_id
