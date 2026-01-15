from uuid import UUID
from pydantic import BaseModel, Field


class Command(BaseModel):
    """Base class for all commands in CQRS pattern"""
    pass


class CreateProduct(Command):
    """Command: Create a new product"""
    product_id: str
    name: str
    price: float = Field(ge=0)
    initial_stock: int = Field(ge=0)
    description: str = ""


class ReserveStock(Command):
    """Command: Reserve stock for a cart"""
    product_id: str
    cart_id: UUID
    quantity: int = Field(gt=0)


class ReleaseReservation(Command):
    """Command: Release stock reservation"""
    product_id: str
    cart_id: UUID
    reason: str = "released"


class CheckoutReservation(Command):
    """Command: Complete checkout and decrease stock"""
    product_id: str
    cart_id: UUID
    order_id: UUID


class IncreaseStock(Command):
    """Command: Increase product stock (restock)"""
    product_id: str
    quantity: int = Field(gt=0)


class ChangePrice(Command):
    """Command: Change product price"""
    product_id: str
    new_price: float = Field(ge=0)


class UpdateProduct(Command):
    """Command: Update product details"""
    product_id: str
    name: str | None = None
    description: str | None = None
