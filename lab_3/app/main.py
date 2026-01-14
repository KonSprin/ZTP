from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.infrastructure.database import Database
from app.api.v1 import cart


# Konfiguracja z environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://cartuser:cartpass@localhost:5432/cartdb"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PRODUCTS_SERVICE_URL = os.getenv("PRODUCTS_SERVICE_URL", "http://localhost:8001")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager - setup and teardown.
    Inicjalizuje połączenie z bazą danych przy starcie aplikacji.
    """
    # Startup
    db = Database(DATABASE_URL)
    await db.create_tables()
    app.state.db = db
    app.state.products_service_url = PRODUCTS_SERVICE_URL
    
    print(f"Database connected: {DATABASE_URL}")
    print(f"Products service: {PRODUCTS_SERVICE_URL}")
    
    yield
    
    # Shutdown
    await db.close()
    print("Database connection closed")


app = FastAPI(
    title="E-commerce Cart Service",
    description="Event-sourced shopping cart with CQRS pattern",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(cart.router)

# Templates setup
templates = Jinja2Templates(directory="app/templates")


# === UI Routes ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with cart mockup UI"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/cart/{cart_id}", response_class=HTMLResponse)
async def cart_view(request: Request, cart_id: str):
    """Cart detail view"""
    return templates.TemplateResponse(
        "cart.html",
        {"request": request, "cart_id": cart_id}
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "cart"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
