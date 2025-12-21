from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from src.routers import notification_router
from src.routers import user_router
from src.routers import stream_router
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
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(notification_router.router)
app.include_router(user_router.router)
app.include_router(stream_router.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {
        "message": "Notification API",
        "version": "2.0.0",
        "endpoints": {
            "users": "/users",
            "notifications": "/notifications",
            "dashboard": "/dashboard"
        }
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the push notifications web dashboard"""
    dashboard_path = Path(__file__).parent / "push_dashboard.html"
    if dashboard_path.exists():
        return dashboard_path.read_text()
    else:
        return """
        <html>
            <body>
                <h1>Dashboard not found</h1>
                <p>Please create push_dashboard.html in the project root</p>
            </body>
        </html>
        """
