from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.domain.cart.events import (
    CartCheckedOut,
    CartCreated,
    CartExpired,
    DomainEvent,
    ItemAddedToCart,
    ItemQuantityChanged,
    ItemRemovedFromCart,
    ProductReservationReleased,
    ProductReserved,
)


class CartItem:
    """Value object representing an item in the cart"""
    
    def __init__(self, product_id: str, product_name: str, price: float, quantity: int):
        self.product_id = product_id
        self.product_name = product_name
        self.price = price
        self.quantity = quantity

    @property
    def total_price(self) -> float:
        return self.price * self.quantity


class CartAggregate:
    """
    Cart Aggregate Root - zarządza stanem koszyka poprzez event sourcing.
    
    Ważne zasady:
    1. Stan jest odtwarzany z eventów (replay)
    2. Wszystkie zmiany stanu poprzez apply_event()
    3. Biznesowa logika walidacji w metodach command (add_item, remove_item etc.)
    4. Optimistic locking przez version
    """

    def __init__(self, cart_id: UUID):
        self.cart_id = cart_id
        self.user_id: str | None = None
        self.items: dict[str, CartItem] = {}
        self.status: str = "PENDING"  # PENDING, CHECKED_OUT, EXPIRED
        self.version: int = 0
        self.created_at: datetime | None = None
        self.last_activity: datetime | None = None
        self.uncommitted_events: list[DomainEvent] = []

    # === Event Application (Replay) ===
    
    def apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        """
        Apply event to aggregate state.
        is_new=True: nowy event (dodaj do uncommitted)
        is_new=False: replay z event store (nie dodawaj do uncommitted)
        """
        # Route to specific handler
        handler_name = f"_apply_{event.event_type}"
        handler = getattr(self, handler_name, None)
        
        if handler is None:
            raise ValueError(f"No handler for event type: {event.event_type}")
        
        handler(event)
        
        if is_new:
            self.uncommitted_events.append(event)

    def _apply_CartCreated(self, event: CartCreated) -> None:
        self.user_id = event.user_id
        self.status = "PENDING"
        self.created_at = event.occurred_at
        self.last_activity = event.occurred_at
        self.version = event.aggregate_version

    def _apply_ItemAddedToCart(self, event: ItemAddedToCart) -> None:
        if event.product_id in self.items:
            # Jeśli produkt już istnieje, zwiększ quantity
            self.items[event.product_id].quantity += event.quantity
        else:
            self.items[event.product_id] = CartItem(
                product_id=event.product_id,
                product_name=event.product_name,
                price=event.price,
                quantity=event.quantity
            )
        self.last_activity = event.occurred_at
        self.version = event.aggregate_version

    def _apply_ItemRemovedFromCart(self, event: ItemRemovedFromCart) -> None:
        self.items.pop(event.product_id, None)
        self.last_activity = event.occurred_at
        self.version = event.aggregate_version

    def _apply_ItemQuantityChanged(self, event: ItemQuantityChanged) -> None:
        if event.product_id in self.items:
            self.items[event.product_id].quantity = event.new_quantity
        self.last_activity = event.occurred_at
        self.version = event.aggregate_version

    def _apply_CartCheckedOut(self, event: CartCheckedOut) -> None:
        self.status = "CHECKED_OUT"
        self.last_activity = event.occurred_at
        self.version = event.aggregate_version

    def _apply_CartExpired(self, event: CartExpired) -> None:
        self.status = "EXPIRED"
        self.last_activity = event.occurred_at
        self.version = event.aggregate_version

    def _apply_ProductReserved(self, event: ProductReserved) -> None:
        # Do implementacji w ramach bonusowych wymagań
        self.version = event.aggregate_version

    def _apply_ProductReservationReleased(self, event: ProductReservationReleased) -> None:
        # Do implementacji w ramach bonusowych wymagań
        self.version = event.aggregate_version

    # === Business Logic (Commands) ===

    def create(self, user_id: str) -> None:
        """Create new cart - business logic validation"""
        if self.user_id is not None:
            raise ValueError("Cart already created")

        event = CartCreated(
            event_id=uuid4(),
            aggregate_id=self.cart_id,
            aggregate_version=self.version + 1,
            user_id=user_id
        )
        self.apply_event(event)

    def add_item(self, product_id: str, product_name: str, price: float, quantity: int) -> None:
        """Add item to cart - business logic validation"""
        if self.status != "PENDING":
            raise ValueError(f"Cannot add items to cart with status: {self.status}")
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if price < 0:
            raise ValueError("Price cannot be negative")

        event = ItemAddedToCart(
            event_id=uuid4(),
            aggregate_id=self.cart_id,
            aggregate_version=self.version + 1,
            product_id=product_id,
            product_name=product_name,
            price=price,
            quantity=quantity
        )
        self.apply_event(event)

    def remove_item(self, product_id: str) -> None:
        """Remove item from cart - business logic validation"""
        if self.status != "PENDING":
            raise ValueError(f"Cannot remove items from cart with status: {self.status}")
        
        if product_id not in self.items:
            raise ValueError(f"Product {product_id} not found in cart")

        event = ItemRemovedFromCart(
            event_id=uuid4(),
            aggregate_id=self.cart_id,
            aggregate_version=self.version + 1,
            product_id=product_id
        )
        self.apply_event(event)

    def change_quantity(self, product_id: str, new_quantity: int) -> None:
        """Change item quantity - business logic validation"""
        if self.status != "PENDING":
            raise ValueError(f"Cannot change quantity in cart with status: {self.status}")
        
        if product_id not in self.items:
            raise ValueError(f"Product {product_id} not found in cart")
        
        if new_quantity <= 0:
            raise ValueError("Quantity must be positive")

        old_quantity = self.items[product_id].quantity

        event = ItemQuantityChanged(
            event_id=uuid4(),
            aggregate_id=self.cart_id,
            aggregate_version=self.version + 1,
            product_id=product_id,
            new_quantity=new_quantity,
            old_quantity=old_quantity
        )
        self.apply_event(event)

    def checkout(self, order_id: UUID) -> None:
        """Checkout cart - business logic validation"""
        if self.status != "PENDING":
            raise ValueError(f"Cannot checkout cart with status: {self.status}")
        
        if not self.items:
            raise ValueError("Cannot checkout empty cart")

        total_amount = sum(item.total_price for item in self.items.values())

        event = CartCheckedOut(
            event_id=uuid4(),
            aggregate_id=self.cart_id,
            aggregate_version=self.version + 1,
            order_id=order_id,
            total_amount=total_amount
        )
        self.apply_event(event)

    def expire(self, reason: str = "15_minute_timeout") -> None:
        """Expire cart - business logic validation"""
        if self.status != "PENDING":
            raise ValueError(f"Cannot expire cart with status: {self.status}")

        event = CartExpired(
            event_id=uuid4(),
            aggregate_id=self.cart_id,
            aggregate_version=self.version + 1,
            reason=reason
        )
        self.apply_event(event)

    # === Helpers ===

    @property
    def total_amount(self) -> float:
        """Calculate total cart amount"""
        return sum(item.total_price for item in self.items.values())

    @property
    def item_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.values())

    def is_expired(self, timeout_minutes: int = 15) -> bool:
        """Check if cart should be expired based on inactivity"""
        if self.status != "PENDING" or self.last_activity is None:
            return False
        
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        return self.last_activity < timeout_threshold

    def clear_uncommitted_events(self) -> None:
        """Clear uncommitted events after persistence"""
        self.uncommitted_events = []

    def get_uncommitted_events(self) -> list[DomainEvent]:
        """Get events that need to be persisted"""
        return self.uncommitted_events.copy()
