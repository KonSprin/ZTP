from uuid import UUID
from pydantic import BaseModel, Field


class Command(BaseModel):
    """Base class for all commands in CQRS pattern"""
    pass


class CreateCart(Command):
    """Command: Create a new shopping cart for a user"""
    cart_id: UUID
    user_id: str


class AddItemToCart(Command):
    """Command: Add a product to the shopping cart"""
    cart_id: UUID
    product_id: str
    quantity: int = Field(gt=0)


class RemoveItemFromCart(Command):
    """Command: Remove a product from the shopping cart"""
    cart_id: UUID
    product_id: str


class ChangeItemQuantity(Command):
    """Command: Update quantity of a product in cart"""
    cart_id: UUID
    product_id: str
    new_quantity: int = Field(gt=0)


class CheckoutCart(Command):
    """Command: Finalize cart and create an order"""
    cart_id: UUID
    order_id: UUID


class ExpireCart(Command):
    """Command: Expire cart due to timeout (optional feature)"""
    cart_id: UUID
    reason: str = "15_minute_timeout"
