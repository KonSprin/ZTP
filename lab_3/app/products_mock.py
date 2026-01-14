from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Products Service (Mock)")


class Product(BaseModel):
    id: str
    name: str
    price: float
    stock: int
    description: str


# Mock product database
PRODUCTS = {
    "P001": Product(
        id="P001",
        name="Dell XPS 13",
        price=4999.99,
        stock=10,
        description="13-inch ultrabook with Intel i7"
    ),
    "P002": Product(
        id="P002",
        name="Klawiatura Logitech",
        price=399.99,
        stock=25,
        description="Mechanical keyboard with RGB lighting"
    ),
    "P003": Product(
        id="P003",
        name="Logitech MX Master",
        price=349.99,
        stock=50,
        description="Wireless ergonomic mouse"
    ),
    "P004": Product(
        id="P004",
        name="Monitor 27 cali 4K Dell",
        price=1999.99,
        stock=15,
        description="27-inch 4K IPS monitor"
    ),
    "P005": Product(
        id="P005",
        name="Słuchawki Sony WH-1000XM5",
        price=1499.99,
        stock=30,
        description="Noise-cancelling wireless headphones"
    ),
}


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID"""
    product = PRODUCTS.get(product_id)
    
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    return product.model_dump()


@app.get("/products")
async def list_products():
    """List all products"""
    return {"products": [p.model_dump() for p in PRODUCTS.values()]}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}
