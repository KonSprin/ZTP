from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.infrastructure.database_products import ProductDatabase
from app.domain.product.commands import CreateProduct, IncreaseStock, ChangePrice, UpdateProduct
from app.infrastructure.repositories.product_event_store import ProductEventStore
from app.infrastructure.repositories.product_read_model import (
    ProductReadModelRepository,
    ProductReadModel
)
from app.domain.product.aggregate import ProductAggregate


# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://cartuser:cartpass@localhost:5432/cartdb"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    # Startup
    db = ProductDatabase(DATABASE_URL)
    await db.create_tables()
    
    # Initialize with sample products
    await initialize_products(db)
    
    app.state.db = db
    print(f"Products database connected: {DATABASE_URL}")
    
    yield
    
    # Shutdown
    await db.close()
    print("Products database connection closed")


app = FastAPI(
    title="Products Service",
    description="Event-sourced products with stock reservations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Dependency Injection ===

async def get_db_session() -> AsyncSession: # type: ignore
    """Get database session from app state"""
    db: ProductDatabase = app.state.db
    async for session in db.get_session(): # type: ignore
        yield session # type: ignore


# === Request/Response Models ===

class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    stock: int  # available_stock for backward compatibility
    total_stock: int
    reserved_stock: int
    available_stock: int
    description: str


class CreateProductRequest(BaseModel):
    id: str
    name: str
    price: float = Field(ge=0)
    initial_stock: int = Field(ge=0)
    description: str = ""


class IncreaseStockRequest(BaseModel):
    quantity: int = Field(gt=0)


# === API Endpoints ===

@app.get("/products/{product_id}")
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get product by ID"""
    repo = ProductReadModelRepository(session)
    product = await repo.get_product(product_id)
    
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    return ProductResponse(
        id=product.product_id,
        name=product.name,
        price=product.price,
        stock=product.available_stock,  # backward compatibility
        total_stock=product.total_stock,
        reserved_stock=product.reserved_stock,
        available_stock=product.available_stock,
        description=product.description,
    )


@app.get("/products")
async def list_products(
    available_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session)
):
    """List all products"""
    repo = ProductReadModelRepository(session)
    products = await repo.list_products(available_only, limit, offset)
    
    return {
        "products": [
            ProductResponse(
                id=p.product_id,
                name=p.name,
                price=p.price,
                stock=p.available_stock,
                total_stock=p.total_stock,
                reserved_stock=p.reserved_stock,
                available_stock=p.available_stock,
                description=p.description,
            )
            for p in products
        ]
    }


@app.post("/products", status_code=201)
async def create_product(
    payload: CreateProductRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Create new product"""
    try:
        event_store = ProductEventStore(session)
        read_model_repo = ProductReadModelRepository(session)
        
        # Check if exists
        existing = await event_store.load_aggregate(payload.id)
        if existing is not None:
            raise HTTPException(status_code=400, detail="Product already exists")
        
        # Create aggregate
        aggregate = ProductAggregate(payload.id)
        aggregate.create(
            name=payload.name,
            price=payload.price,
            initial_stock=payload.initial_stock,
            description=payload.description
        )
        
        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        await event_store.save_events(
            aggregate_id=payload.id,
            events=uncommitted_events,
            expected_version=0
        )
        
        # Create read model
        await read_model_repo.create_projection(
            product_id=payload.id,
            name=payload.name,
            price=payload.price,
            description=payload.description,
            total_stock=payload.initial_stock,
            created_at=aggregate.created_at # type: ignore
        )
        
        return {"message": "Product created", "product_id": payload.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/products/{product_id}/restock")
async def increase_stock(
    product_id: str,
    payload: IncreaseStockRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Increase product stock (restock)"""
    try:
        event_store = ProductEventStore(session)
        read_model_repo = ProductReadModelRepository(session)
        
        # Load aggregate
        aggregate = await event_store.load_aggregate(product_id)
        if aggregate is None:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Increase stock
        aggregate.increase_stock(payload.quantity)
        
        # Save events
        uncommitted_events = aggregate.get_uncommitted_events()
        await event_store.save_events(
            aggregate_id=product_id,
            events=uncommitted_events,
            expected_version=aggregate.version - len(uncommitted_events)
        )
        
        # Update read model
        await read_model_repo.update_projection(
            product_id=aggregate.product_id,
            name=aggregate.name, # type: ignore
            price=aggregate.price,
            description=aggregate.description,
            total_stock=aggregate.total_stock,
            reserved_stock=aggregate.reserved_stock,
            available_stock=aggregate.available_stock,
            version=aggregate.version
        )
        
        return {"message": "Stock increased", "new_total": aggregate.total_stock}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "products"}


# === Initialization ===

async def initialize_products(db: ProductDatabase):
    """Initialize database with sample products if empty"""
    async for session in db.get_session(): # type: ignore
        try:
            repo = ProductReadModelRepository(session)
            existing = await repo.list_products(limit=1)
            
            if existing:
                print("Products already initialized")
                return
            
            # Create sample products
            products = [
                ("P001", "Laptop Dell XPS 13", 4999.99, 10, "13-inch ultrabook with Intel i7"),
                ("P002", "Klawiatura mechaniczna Logitech", 399.99, 25, "Mechanical keyboard with RGB lighting"),
                ("P003", "Mysz bezprzewodowa Logitech MX Master", 349.99, 50, "Wireless ergonomic mouse"),
                ("P004", "Monitor 27 cali 4K Dell", 1999.99, 15, "27-inch 4K IPS monitor"),
                ("P005", "Sluchawki Sony WH-1000XM5", 1499.99, 30, "Noise-cancelling wireless headphones"),
            ]
            
            event_store = ProductEventStore(session)
            
            for product_id, name, price, stock, description in products:
                aggregate = ProductAggregate(product_id)
                aggregate.create(name, price, stock, description)
                
                uncommitted_events = aggregate.get_uncommitted_events()
                await event_store.save_events(product_id, uncommitted_events, 0)
                
                await repo.create_projection(
                    product_id=product_id,
                    name=name,
                    price=price,
                    description=description,
                    total_stock=stock,
                    created_at=aggregate.created_at # type: ignore
                )
            
            print(f"Initialized {len(products)} sample products")
        finally:
            await session.close()
