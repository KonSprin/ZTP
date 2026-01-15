from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.infrastructure.database import Database
from app.api.v1 import cart_integrated
from app.application.cart.expiration_task import CartExpirationBackgroundTask


# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://cartuser:cartpass@localhost:5432/cartdb"
)
# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager - setup and teardown.
    Initializes database and starts background task.
    """
    # Startup
    db = Database(DATABASE_URL)
    await db.create_tables()
    app.state.db = db
    
    # Start cart expiration background task
    expiration_task = CartExpirationBackgroundTask(
        db_factory=db.get_session,
        interval_seconds=60,  # Check every 1 minute
        timeout_minutes=15    # Expire after 15 minutes of inactivity
    )
    await expiration_task.start()
    app.state.expiration_task = expiration_task
    
    print(f"Database connected: {DATABASE_URL}")
    print("Cart expiration task started")
    
    yield
    
    # Shutdown
    await expiration_task.stop()
    await db.close()
    print("Database connection closed")
    print("Cart expiration task stopped")


app = FastAPI(
    title="E-commerce Cart Service",
    description="Event-sourced shopping cart with CQRS and stock reservations",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include integrated API routes
app.include_router(cart_integrated.router)

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
        "app.main_integrated:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
