# main.py
from fastapi import FastAPI
from src.lab_1.routers import users, products, banned_phrases

# from src.lab_1 import models, database
# models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Product Management API",
    description="API do zarządzania produktami z systemem zabronionych fraz i historią zmian",
    version="1.0.0"
)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(banned_phrases.router)

@app.get("/")
def root():
    return {
        "message": "Product Management API",
        "endpoints": {
            "users": "/users",
            "products": "/products",
            "banned_phrases": "/banned-phrases",
            "docs": "/docs"
        }
    }
