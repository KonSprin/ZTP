from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.routers import notification_router
from src import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    database.Base.metadata.create_all(bind=database.engine)
    yield
    # Shutdown

app = FastAPI(
    title="Notification System",
    description="System zarządzania i wysyłki powiadomień",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(notification_router.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {
        "message": "Notification API",
        "endpoints": {
            "users": "/users",
            "notifications": "/notifications"
        }
    }
