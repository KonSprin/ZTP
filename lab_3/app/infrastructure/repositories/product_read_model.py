from datetime import datetime, timezone
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database_products import product_read_model


class ProductReadModel:
    """DTO for product read model"""
    
    def __init__(
        self,
        product_id: str,
        name: str,
        price: float,
        description: str,
        total_stock: int,
        reserved_stock: int,
        available_stock: int,
        version: int,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.description = description
        self.total_stock = total_stock
        self.reserved_stock = reserved_stock
        self.available_stock = available_stock
        self.version = version
        self.created_at = created_at
        self.updated_at = updated_at


class ProductReadModelRepository:
    """
    Read Model Repository for products.
    
    Maintains denormalized projection for fast queries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_product(self, product_id: str) -> ProductReadModel | None:
        """Get product from read model"""
        stmt = select(product_read_model).where(product_read_model.c.product_id == product_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if row is None:
            return None

        return ProductReadModel(
            product_id=row.product_id,
            name=row.name,
            price=row.price,
            description=row.description,
            total_stock=row.total_stock,
            reserved_stock=row.reserved_stock,
            available_stock=row.available_stock,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_products(
        self, 
        available_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> list[ProductReadModel]:
        """List all products with optional filtering"""
        stmt = select(product_read_model)
        
        if available_only:
            stmt = stmt.where(product_read_model.c.available_stock > 0)
        
        stmt = stmt.order_by(product_read_model.c.name).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        return [
            ProductReadModel(
                product_id=row.product_id,
                name=row.name,
                price=row.price,
                description=row.description,
                total_stock=row.total_stock,
                reserved_stock=row.reserved_stock,
                available_stock=row.available_stock,
                version=row.version,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def create_projection(
        self,
        product_id: str,
        name: str,
        price: float,
        description: str,
        total_stock: int,
        created_at: datetime,
    ) -> None:
        """Create initial projection when product is created"""
        stmt = insert(product_read_model).values(
            product_id=product_id,
            name=name,
            price=price,
            description=description,
            total_stock=total_stock,
            reserved_stock=0,
            available_stock=total_stock,
            version=1,
            created_at=created_at,
            updated_at=created_at,
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_projection(
        self,
        product_id: str,
        name: str,
        price: float,
        description: str,
        total_stock: int,
        reserved_stock: int,
        available_stock: int,
        version: int,
    ) -> None:
        """Update projection after events are applied"""
        stmt = (
            update(product_read_model)
            .where(product_read_model.c.product_id == product_id)
            .values(
                name=name,
                price=price,
                description=description,
                total_stock=total_stock,
                reserved_stock=reserved_stock,
                available_stock=available_stock,
                version=version,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
