from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.domain.product.events import (
    DomainEvent,
    ProductCreated,
    ProductStockReserved,
    ProductStockReservationReleased,
    ProductStockIncreased,
    ProductStockDecreased,
    ProductPriceChanged,
    ProductUpdated,
)


class StockReservation:
    """Value object representing a stock reservation"""
    
    def __init__(self, cart_id: UUID, quantity: int, reserved_until: datetime):
        self.cart_id = cart_id
        self.quantity = quantity
        self.reserved_until = reserved_until

    def is_expired(self) -> bool:
        """Check if reservation has expired"""
        return datetime.now(timezone.utc) > self.reserved_until


class ProductAggregate:
    """
    Product Aggregate Root - manages product inventory with reservations.
    
    Business Rules:
    1. Available stock = total_stock - reserved_stock
    2. Reservations expire after 15 minutes
    3. Can't reserve more than available stock
    4. Checkout releases reservation and decreases total stock
    """

    def __init__(self, product_id: str):
        self.product_id = product_id
        self.name: str | None = None
        self.price: float = 0.0
        self.description: str = ""
        self.total_stock: int = 0
        self.reservations: dict[UUID, StockReservation] = {}  # cart_id -> reservation
        self.version: int = 0
        self.created_at: datetime | None = datetime.now(timezone.utc)
        self.uncommitted_events: list[DomainEvent] = []

    # === Event Application (Replay) ===
    
    def apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        """
        Apply event to aggregate state.
        is_new=True: new event (add to uncommitted)
        is_new=False: replay from event store (don't add to uncommitted)
        """
        handler_name = f"_apply_{event.event_type}"
        handler = getattr(self, handler_name, None)
        
        if handler is None:
            raise ValueError(f"No handler for event type: {event.event_type}")
        
        handler(event)
        
        if is_new:
            self.uncommitted_events.append(event)

    def _apply_ProductCreated(self, event: ProductCreated) -> None:
        self.name = event.name
        self.price = event.price
        self.total_stock = event.initial_stock
        self.description = event.description
        self.created_at = event.occurred_at
        self.version = event.aggregate_version

    def _apply_ProductStockReserved(self, event: ProductStockReserved) -> None:
        self.reservations[event.cart_id] = StockReservation(
            cart_id=event.cart_id,
            quantity=event.quantity,
            reserved_until=event.reserved_until
        )
        self.version = event.aggregate_version

    def _apply_ProductStockReservationReleased(self, event: ProductStockReservationReleased) -> None:
        self.reservations.pop(event.cart_id, None)
        self.version = event.aggregate_version

    def _apply_ProductStockIncreased(self, event: ProductStockIncreased) -> None:
        self.total_stock += event.quantity
        self.version = event.aggregate_version

    def _apply_ProductStockDecreased(self, event: ProductStockDecreased) -> None:
        self.total_stock -= event.quantity
        self.version = event.aggregate_version

    def _apply_ProductPriceChanged(self, event: ProductPriceChanged) -> None:
        self.price = event.new_price
        self.version = event.aggregate_version

    def _apply_ProductUpdated(self, event: ProductUpdated) -> None:
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        self.version = event.aggregate_version

    # === Business Logic (Commands) ===

    def create(self, name: str, price: float, initial_stock: int, description: str = "") -> None:
        """Create new product"""
        if self.name is not None:
            raise ValueError("Product already created")
        
        if price < 0:
            raise ValueError("Price cannot be negative")
        
        if initial_stock < 0:
            raise ValueError("Stock cannot be negative")

        event = ProductCreated(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            name=name,
            price=price,
            initial_stock=initial_stock,
            description=description
        )
        self.apply_event(event)

    def reserve_stock(self, cart_id: UUID, quantity: int, reservation_minutes: int = 15) -> None:
        """
        Reserve stock for a cart.
        
        Business rules:
        1. Can't reserve more than available stock
        2. If cart already has reservation, increase it
        3. Reservation expires after 15 minutes
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # Clean up expired reservations first
        self._release_expired_reservations()

        # Check if cart already has reservation
        existing_reservation = self.reservations.get(cart_id)
        if existing_reservation:
            # Cart already has reservation - add to it
            required_additional = quantity
        else:
            required_additional = quantity

        # Check available stock
        available = self.available_stock
        if required_additional > available:
            raise ValueError(
                f"Insufficient stock: requested {required_additional}, "
                f"available {available} (total: {self.total_stock}, reserved: {self.reserved_stock})"
            )

        reserved_until = datetime.now(timezone.utc) + timedelta(minutes=reservation_minutes)
        
        event = ProductStockReserved(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            cart_id=cart_id,
            quantity=quantity,
            reserved_until=reserved_until
        )
        self.apply_event(event)

    def release_reservation(self, cart_id: UUID, reason: str = "released") -> None:
        """Release stock reservation for a cart"""
        reservation = self.reservations.get(cart_id)
        if reservation is None:
            # Already released or never existed - idempotent operation
            return

        event = ProductStockReservationReleased(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            cart_id=cart_id,
            quantity=reservation.quantity,
            reason=reason
        )
        self.apply_event(event)

    def checkout_reservation(self, cart_id: UUID, order_id: UUID) -> None:
        """
        Complete checkout - release reservation and decrease total stock.
        
        This is called when cart is checked out successfully.
        """
        reservation = self.reservations.get(cart_id)
        if reservation is None:
            raise ValueError(f"No reservation found for cart {cart_id}")

        # Release reservation
        self.release_reservation(cart_id, reason="checkout")

        # Decrease total stock (actually sold)
        event = ProductStockDecreased(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            quantity=reservation.quantity,
            order_id=order_id
        )
        self.apply_event(event)

    def increase_stock(self, quantity: int) -> None:
        """Increase stock (restock)"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        event = ProductStockIncreased(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            quantity=quantity
        )
        self.apply_event(event)

    def change_price(self, new_price: float) -> None:
        """Change product price"""
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        
        if new_price == self.price:
            return

        event = ProductPriceChanged(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            old_price=self.price,
            new_price=new_price
        )
        self.apply_event(event)

    def update_details(self, name: str | None = None, description: str | None = None) -> None:
        """Update product details"""
        if name is None and description is None:
            return

        event = ProductUpdated(
            event_id=uuid4(),
            aggregate_id=self.product_id,
            aggregate_version=self.version + 1,
            name=name,
            description=description
        )
        self.apply_event(event)

    # === Helpers ===

    @property
    def reserved_stock(self) -> int:
        """Calculate total reserved stock (excluding expired)"""
        self._release_expired_reservations()
        return sum(r.quantity for r in self.reservations.values())

    @property
    def available_stock(self) -> int:
        """Calculate available stock (total - reserved)"""
        return self.total_stock - self.reserved_stock

    def _release_expired_reservations(self) -> None:
        """Internal: Release all expired reservations"""
        expired_carts = [
            cart_id for cart_id, reservation in self.reservations.items()
            if reservation.is_expired()
        ]
        
        for cart_id in expired_carts:
            self.release_reservation(cart_id, reason="timeout")

    def get_reservation(self, cart_id: UUID) -> StockReservation | None:
        """Get reservation for specific cart"""
        return self.reservations.get(cart_id)

    def clear_uncommitted_events(self) -> None:
        """Clear uncommitted events after persistence"""
        self.uncommitted_events = []

    def get_uncommitted_events(self) -> list[DomainEvent]:
        """Get events that need to be persisted"""
        return self.uncommitted_events.copy()
