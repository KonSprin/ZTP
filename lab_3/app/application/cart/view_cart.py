from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.read_model import ReadModelRepository, CartReadModel


class ViewCartQuery:
    """
    Query: Pobierz zawartość koszyka.
    
    To jest query side w CQRS - używamy read model zamiast replayu eventów.
    Read model można dodatkowo cache'ować w Redis dla jeszcze szybszych odczytów.
    """

    def __init__(self, session: AsyncSession):
        self.read_model_repo = ReadModelRepository(session)

    async def execute(self, cart_id: UUID) -> CartReadModel | None:
        """
        Get cart details from read model.
        
        Returns:
            CartReadModel or None if cart doesn't exist
        """
        return await self.read_model_repo.get_cart(cart_id)


class ViewUserCartsQuery:
    """Query: Pobierz wszystkie koszyki użytkownika"""

    def __init__(self, session: AsyncSession):
        self.read_model_repo = ReadModelRepository(session)

    async def execute(self, user_id: str, status: str | None = None) -> list[CartReadModel]:
        """
        Get all carts for user, optionally filtered by status.
        
        Args:
            user_id: User identifier
            status: Optional status filter (PENDING, CHECKED_OUT, EXPIRED)
        
        Returns:
            List of user's carts
        """
        return await self.read_model_repo.get_user_carts(user_id, status)
