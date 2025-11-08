from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import ValidationError
from .. import schemas, database
from ..services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])
service = ProductService()

@router.get("", response_model=List[schemas.Product])
def get_products(db = Depends(database.get_db)):
    """Pobiera listę wszystkich produktów"""
    return service.get_products(db)

@router.get("/{id}", response_model=schemas.Product)
def get_product(id: int, db = Depends(database.get_db)):
    """Pobiera szczegóły produktu po ID"""
    product = service.get_product(db, id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product

@router.post("", response_model=schemas.Product, status_code=201)
def create_product(product: schemas.ProductCreate, db=Depends(database.get_db)):
    """
    Tworzy nowy produkt.
    
    Walidacje:
    - Nazwa: 3-20 znaków, tylko litery i cyfry, unikalna
    - Cena: zależna od kategorii (Elektronika: 50-50000, Książki: 5-500, Odzież: 10-5000)
    - Ilość: liczba całkowita >= 0
    - Kategoria: Elektronika, Książki lub Odzież
    - Brak zabronionych fraz w nazwie
    """
    try:
        return service.create_product(db, product)
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

@router.put("/{id}", response_model=schemas.Product)
def update_product(id: int, product: schemas.ProductUpdate, db=Depends(database.get_db)):
    """
    Aktualizuje cały produkt (PUT).
    
    Wszystkie pola są wymagane. Walidacje jak przy tworzeniu produktu.
    """
    try:
        updated_product = service.update_product(db, id, product)
        if not updated_product:
            raise HTTPException(404, "Product not found")
        return updated_product
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

@router.patch("/{id}", response_model=schemas.Product)
def patch_product(id: int, data: schemas.ProductPartialUpdate, db=Depends(database.get_db)):
    """
    Częściowo aktualizuje produkt (PATCH).
    
    Można podać tylko wybrane pola do aktualizacji.
    Walidacje stosowane są do wszystkich podanych pól.
    """
    try:
        # Konwersja do dict z pominięciem None
        update_data = data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(400, "No fields to update")
        
        updated_product = service.patch_product(db, id, update_data)
        if not updated_product:
            raise HTTPException(404, "Product not found")
        return updated_product
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

@router.delete("/{id}")
def delete_product(id: int, db=Depends(database.get_db)):
    """Usuwa produkt"""
    result = service.delete_product(db, id)
    if result["code"] == 1:
        raise HTTPException(404, "Product not found")
    return result

@router.get("/{id}/history", response_model=List[schemas.ProductHistory])
def get_product_history(id: int, db=Depends(database.get_db)):
    """Pobiera historię zmian produktu"""
    product = service.get_product(db, id)
    if not product:
        raise HTTPException(404, "Product not found")
    return service.get_product_history(db, id)

@router.get("/history/all", response_model=List[schemas.ProductHistory])
def get_all_history(db=Depends(database.get_db)):
    """Pobiera całą historię zmian wszystkich produktów"""
    return service.get_all_history(db)
