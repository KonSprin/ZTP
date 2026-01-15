from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for all domain events in event sourcing"""
    event_id: UUID
    aggregate_id: str
    aggregate_version: int
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str

    class Config:
        frozen = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary for storage"""
        return self.model_dump(mode='json')


class ProductCreated(DomainEvent):
    """Event: Product was created in inventory"""
    event_type: str = "ProductCreated"
    name: str
    price: float
    initial_stock: int
    description: str


class ProductStockReserved(DomainEvent):
    """Event: Stock was reserved for a cart"""
    event_type: str = "ProductStockReserved"
    cart_id: UUID
    quantity: int
    reserved_until: datetime


class ProductStockReservationReleased(DomainEvent):
    """Event: Stock reservation was released"""
    event_type: str = "ProductStockReservationReleased"
    cart_id: UUID
    quantity: int
    reason: str  # "timeout", "checkout", "cart_expired", "item_removed"


class ProductStockIncreased(DomainEvent):
    """Event: Stock was increased (restock)"""
    event_type: str = "ProductStockIncreased"
    quantity: int


class ProductStockDecreased(DomainEvent):
    """Event: Stock was decreased (checkout completed)"""
    event_type: str = "ProductStockDecreased"
    quantity: int
    order_id: UUID


class ProductPriceChanged(DomainEvent):
    """Event: Product price was changed"""
    event_type: str = "ProductPriceChanged"
    old_price: float
    new_price: float


class ProductUpdated(DomainEvent):
    """Event: Product details were updated"""
    event_type: str = "ProductUpdated"
    name: str | None = None
    description: str | None = None
