from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for all domain events in event sourcing"""
    event_id: UUID
    aggregate_id: UUID
    aggregate_version: int
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    event_type: str

    class Config:
        frozen = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary for storage"""
        return self.model_dump(mode='json')


class CartCreated(DomainEvent):
    """Event: User created a new shopping cart"""
    event_type: str = "CartCreated"
    user_id: str


class ItemAddedToCart(DomainEvent):
    """Event: User added a product to cart"""
    event_type: str = "ItemAddedToCart"
    product_id: str
    product_name: str
    price: float
    quantity: int


class ItemRemovedFromCart(DomainEvent):
    """Event: User removed a product from cart"""
    event_type: str = "ItemRemovedFromCart"
    product_id: str


class ItemQuantityChanged(DomainEvent):
    """Event: User changed quantity of a product in cart"""
    event_type: str = "ItemQuantityChanged"
    product_id: str
    new_quantity: int
    old_quantity: int


class CartCheckedOut(DomainEvent):
    """Event: User finalized cart and created an order"""
    event_type: str = "CartCheckedOut"
    order_id: UUID
    total_amount: float


class CartExpired(DomainEvent):
    """Event: Cart expired due to 15min timeout (optional feature)"""
    event_type: str = "CartExpired"
    reason: str = "15_minute_timeout"


class ProductReserved(DomainEvent):
    """Event: Product was reserved in this cart (optional feature)"""
    event_type: str = "ProductReserved"
    product_id: str
    reserved_until: datetime


class ProductReservationReleased(DomainEvent):
    """Event: Product reservation was released (optional feature)"""
    event_type: str = "ProductReservationReleased"
    product_id: str
    reason: str
