import pytest
from uuid import uuid4

from app.domain.cart.aggregate import CartAggregate
from app.domain.cart.events import CartCreated, ItemAddedToCart, CartCheckedOut


class TestCartAggregate:
    """
    Unit testy dla CartAggregate.
    
    Zaletą clean architecture i event sourcing:
    - Testy bez bazy danych
    - Testy bez HTTP
    - Szybkie i izolowane
    """

    def test_create_cart(self):
        """Test: tworzenie nowego koszyka"""
        cart_id = uuid4()
        user_id = "user_123"
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id=user_id)
        
        # Sprawdź stan agregatu
        assert aggregate.user_id == user_id
        assert aggregate.status == "PENDING"
        assert aggregate.version == 1
        assert len(aggregate.items) == 0
        
        # Sprawdź czy wygenerowano event
        events = aggregate.get_uncommitted_events()
        assert len(events) == 1
        assert isinstance(events[0], CartCreated)
        assert events[0].user_id == user_id

    def test_cannot_create_cart_twice(self):
        """Test: nie można utworzyć koszyka dwa razy"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        
        with pytest.raises(ValueError, match="Cart already created"):
            aggregate.create(user_id="user_456")

    def test_add_item_to_cart(self):
        """Test: dodawanie produktu do koszyka"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        aggregate.add_item(
            product_id="P001",
            product_name="Laptop",
            price=4999.99,
            quantity=2
        )
        
        # Sprawdź stan
        assert len(aggregate.items) == 1
        assert aggregate.items["P001"].quantity == 2
        assert aggregate.total_amount == 9999.98
        assert aggregate.item_count == 2
        assert aggregate.version == 2
        
        # Sprawdź eventy
        events = aggregate.get_uncommitted_events()
        assert len(events) == 2
        assert isinstance(events[1], ItemAddedToCart)
        assert events[1].product_id == "P001"
        assert events[1].quantity == 2

    def test_add_same_item_increases_quantity(self):
        """Test: dodanie tego samego produktu zwiększa quantity"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        aggregate.add_item("P001", "Laptop", 4999.99, 1)
        aggregate.add_item("P001", "Laptop", 4999.99, 2)
        
        assert aggregate.items["P001"].quantity == 3
        assert aggregate.item_count == 3

    def test_cannot_add_item_with_negative_quantity(self):
        """Test: nie można dodać produktu z ujemną ilością"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        
        with pytest.raises(ValueError, match="Quantity must be positive"):
            aggregate.add_item("P001", "Laptop", 4999.99, -1)

    def test_remove_item_from_cart(self):
        """Test: usuwanie produktu z koszyka"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        aggregate.add_item("P001", "Laptop", 4999.99, 2)
        aggregate.remove_item("P001")
        
        assert len(aggregate.items) == 0
        assert aggregate.total_amount == 0
        assert aggregate.item_count == 0

    def test_cannot_remove_nonexistent_item(self):
        """Test: nie można usunąć produktu, którego nie ma"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        
        with pytest.raises(ValueError, match="Product P001 not found"):
            aggregate.remove_item("P001")

    def test_checkout_cart(self):
        """Test: finalizacja koszyka"""
        cart_id = uuid4()
        order_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        aggregate.add_item("P001", "Laptop", 4999.99, 1)
        aggregate.checkout(order_id=order_id)
        
        assert aggregate.status == "CHECKED_OUT"
        
        events = aggregate.get_uncommitted_events()
        assert isinstance(events[-1], CartCheckedOut)
        assert events[-1].order_id == order_id
        assert events[-1].total_amount == 4999.99

    def test_cannot_checkout_empty_cart(self):
        """Test: nie można sfinalizować pustego koszyka"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        
        with pytest.raises(ValueError, match="Cannot checkout empty cart"):
            aggregate.checkout(order_id=uuid4())

    def test_cannot_modify_checked_out_cart(self):
        """Test: nie można modyfikować sfinalizowanego koszyka"""
        cart_id = uuid4()
        
        aggregate = CartAggregate(cart_id)
        aggregate.create(user_id="user_123")
        aggregate.add_item("P001", "Laptop", 4999.99, 1)
        aggregate.checkout(order_id=uuid4())
        
        with pytest.raises(ValueError, match="Cannot add items to cart with status: CHECKED_OUT"):
            aggregate.add_item("P002", "Mouse", 99.99, 1)

    def test_event_replay(self):
        """
        Test: odtworzenie stanu z eventów (replay).
        To jest serce event sourcingu!
        """
        cart_id = uuid4()
        
        # Utwórz agregat i wykonaj operacje
        aggregate1 = CartAggregate(cart_id)
        aggregate1.create(user_id="user_123")
        aggregate1.add_item("P001", "Laptop", 4999.99, 2)
        aggregate1.add_item("P002", "Mouse", 99.99, 1)
        
        # Zapisz eventy
        events = aggregate1.get_uncommitted_events()
        
        # Odtwórz nowy agregat z eventów (replay)
        aggregate2 = CartAggregate(cart_id)
        for event in events:
            aggregate2.apply_event(event, is_new=False)
        
        # Stan powinien być identyczny
        assert aggregate2.user_id == "user_123"
        assert aggregate2.status == "PENDING"
        assert aggregate2.version == 3
        assert len(aggregate2.items) == 2
        assert aggregate2.items["P001"].quantity == 2
        assert aggregate2.items["P002"].quantity == 1
        assert aggregate2.total_amount == pytest.approx(10099.97)
        
        # Replay nie powinien dodawać do uncommitted_events
        assert len(aggregate2.get_uncommitted_events()) == 0
