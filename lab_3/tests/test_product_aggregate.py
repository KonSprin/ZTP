import pytest
from uuid import uuid4

from app.domain.product.aggregate import ProductAggregate

class TestCartAggregate:
    """
    Unit testy dla ProductAggregate.
    """

    # Test product reservation
    def test_reserve_stock(self):
        aggregate = ProductAggregate("P001")
        aggregate.create("Laptop", 4999.99, 10, "")
        
        aggregate.reserve_stock(cart_id=uuid4(), quantity=3)
        
        assert aggregate.reserved_stock == 3
        assert aggregate.available_stock == 7

    # Test insufficient stock
    def test_insufficient_stock(self):
        aggregate = ProductAggregate("P001")
        aggregate.create("Laptop", 4999.99, 5, "")
        
        with pytest.raises(ValueError, match="Insufficient stock"):
            aggregate.reserve_stock(cart_id=uuid4(), quantity=10)
