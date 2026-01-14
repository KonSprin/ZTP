from uuid import UUID
from datetime import datetime
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import cart_read_model


class CartReadModel:
    """DTO for cart read model"""
    
    def __init__(
        self,
        cart_id: UUID,
        user_id: str,
        status: str,
        items: list[dict],
        total_amount: float,
        item_count: int,
        version: int,
        created_at: datetime,
        last_activity: datetime,
    ):
        self.cart_id = cart_id
        self.user_id = user_id
        self.status = status
        self.items = items
        self.total_amount = total_amount
        self.item_count = item_count
        self.version = version
        self.created_at = created_at
        self.last_activity = last_activity


class ReadModelRepository:
    """
    Read Model Repository - zarządza zdenormalizowaną projekcją dla szybkich odczytów.
    
    Read model jest aktualizowany asynchronicznie po zapisaniu eventów.
    Można go cache'ować w Redis dla jeszcze szybszych odczytów.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_cart(self, cart_id: UUID) -> CartReadModel | None:
        """Get cart from read model"""
        stmt = select(cart_read_model).where(cart_read_model.c.cart_id == cart_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if row is None:
            return None

        return CartReadModel(
            cart_id=row.cart_id,
            user_id=row.user_id,
            status=row.status,
            items=row.items,
            total_amount=row.total_amount,
            item_count=row.item_count,
            version=row.version,
            created_at=row.created_at,
            last_activity=row.last_activity,
        )

    async def get_user_carts(
        self, 
        user_id: str, 
        status: str | None = None
    ) -> list[CartReadModel]:
        """Get all carts for user, optionally filtered by status"""
        stmt = select(cart_read_model).where(cart_read_model.c.user_id == user_id)
        
        if status:
            stmt = stmt.where(cart_read_model.c.status == status)
        
        stmt = stmt.order_by(cart_read_model.c.last_activity.desc())

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        return [
            CartReadModel(
                cart_id=row.cart_id,
                user_id=row.user_id,
                status=row.status,
                items=row.items,
                total_amount=row.total_amount,
                item_count=row.item_count,
                version=row.version,
                created_at=row.created_at,
                last_activity=row.last_activity,
            )
            for row in rows
        ]

    async def create_projection(
        self,
        cart_id: UUID,
        user_id: str,
        created_at: datetime,
    ) -> None:
        """Create initial projection when cart is created"""
        stmt = insert(cart_read_model).values(
            cart_id=cart_id,
            user_id=user_id,
            status="PENDING",
            items=[],
            total_amount=0.0,
            item_count=0,
            version=1,
            created_at=created_at,
            last_activity=created_at,
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_projection(
        self,
        cart_id: UUID,
        status: str,
        items: list[dict],
        total_amount: float,
        item_count: int,
        version: int,
        last_activity: datetime,
    ) -> None:
        """Update projection after events are applied"""
        stmt = (
            update(cart_read_model)
            .where(cart_read_model.c.cart_id == cart_id)
            .values(
                status=status,
                items=items,
                total_amount=total_amount,
                item_count=item_count,
                version=version,
                last_activity=last_activity,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_projection(self, cart_id: UUID) -> None:
        """Delete projection (if needed for cleanup)"""
        stmt = delete(cart_read_model).where(cart_read_model.c.cart_id == cart_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_expired_carts(self, timeout_minutes: int = 15) -> list[UUID]:
        """Get cart IDs that should be expired due to inactivity"""
        from datetime import timedelta
        
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        stmt = (
            select(cart_read_model.c.cart_id)
            .where(cart_read_model.c.status == "PENDING")
            .where(cart_read_model.c.last_activity < timeout_threshold)
        )
        
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        return [row.cart_id for row in rows]
