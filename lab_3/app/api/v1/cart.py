from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import Database
from app.application.cart.create_cart import CreateCartUseCase
from app.application.cart.add_item import AddItemToCartUseCase, ProductNotFoundError
from app.application.cart.remove_item import RemoveItemFromCartUseCase
from app.application.cart.view_cart import ViewCartQuery, ViewUserCartsQuery
from app.application.cart.checkout import CheckoutCartUseCase
from app.domain.cart.commands import (
    CreateCart,
    AddItemToCart,
    RemoveItemFromCart,
    CheckoutCart,
)
from app.infrastructure.repositories.event_store import ConcurrencyException


router = APIRouter(prefix="/api/v1/cart", tags=["cart"])
templates = Jinja2Templates(directory="app/templates")


# === Request/Response Models ===

class CreateCartRequest(BaseModel):
    user_id: str


class CreateCartResponse(BaseModel):
    cart_id: UUID


class AddItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)


class RemoveItemRequest(BaseModel):
    product_id: str


class CheckoutResponse(BaseModel):
    order_id: UUID
    cart_id: UUID
    total_amount: float


# === Dependency Injection ===

async def get_db_session(request: Request) -> AsyncSession:
    """Get database session from app state"""
    db: Database = request.app.state.db
    async for session in db.get_session():
        yield session


def get_products_service_url(request: Request) -> str:
    """Get products service URL from app state"""
    return request.app.state.products_service_url


# === Command Endpoints (Write) ===

@router.post("/", response_model=CreateCartResponse, status_code=201)
async def create_cart(
    payload: CreateCartRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new shopping cart for a user.
    
    Command side of CQRS.
    """
    try:
        cart_id = uuid4()
        command = CreateCart(cart_id=cart_id, user_id=payload.user_id)
        
        use_case = CreateCartUseCase(session)
        created_cart_id = await use_case.execute(command)
        
        return CreateCartResponse(cart_id=created_cart_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/{cart_id}/items", status_code=201)
async def add_item_to_cart(
    cart_id: UUID,
    payload: AddItemRequest,
    session: AsyncSession = Depends(get_db_session),
    products_service_url: str = Depends(get_products_service_url),
):
    """
    Add a product to the cart.
    
    Communicates with products service via HTTP.
    Implements retry on concurrency conflicts (optimistic locking).
    """
    try:
        command = AddItemToCart(
            cart_id=cart_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
        )
        
        use_case = AddItemToCartUseCase(session, products_service_url)
        await use_case.execute(command)
        
        return {"message": "Item added successfully"}
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConcurrencyException as e:
        raise HTTPException(status_code=409, detail=f"Concurrency conflict: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete("/{cart_id}/items", status_code=200)
async def remove_item_from_cart(
    cart_id: UUID,
    payload: RemoveItemRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Remove a product from the cart"""
    try:
        command = RemoveItemFromCart(
            cart_id=cart_id,
            product_id=payload.product_id,
        )
        
        use_case = RemoveItemFromCartUseCase(session)
        await use_case.execute(command)
        
        return {"message": "Item removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConcurrencyException as e:
        raise HTTPException(status_code=409, detail=f"Concurrency conflict: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
async def checkout_cart(
    cart_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Finalize cart and create an order.
    
    Generates CartCheckedOut event.
    In the future, this event can be published to message broker
    for order domain to consume.
    """
    try:
        order_id = uuid4()
        command = CheckoutCart(cart_id=cart_id, order_id=order_id)
        
        use_case = CheckoutCartUseCase(session)
        result = await use_case.execute(command)
        
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConcurrencyException as e:
        raise HTTPException(status_code=409, detail=f"Concurrency conflict: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# === Query Endpoints (Read) ===

@router.get("/{cart_id}")
async def get_cart(
    cart_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get cart details.
    
    Query side of CQRS - reads from read model.
    """
    try:
        query = ViewCartQuery(session)
        cart = await query.execute(cart_id)
        
        if cart is None:
            raise HTTPException(status_code=404, detail="Cart not found")
        
        return {
            "cart_id": cart.cart_id,
            "user_id": cart.user_id,
            "status": cart.status,
            "items": cart.items,
            "total_amount": cart.total_amount,
            "item_count": cart.item_count,
            "version": cart.version,
            "created_at": cart.created_at,
            "last_activity": cart.last_activity,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/user/{user_id}/carts")
async def get_user_carts(
    user_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get all carts for a user, optionally filtered by status"""
    try:
        query = ViewUserCartsQuery(session)
        carts = await query.execute(user_id, status)
        
        return {
            "carts": [
                {
                    "cart_id": cart.cart_id,
                    "user_id": cart.user_id,
                    "status": cart.status,
                    "item_count": cart.item_count,
                    "total_amount": cart.total_amount,
                    "last_activity": cart.last_activity,
                }
                for cart in carts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
