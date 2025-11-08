from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo
from datetime import datetime
from typing import Optional, Literal
import re

# User schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int

    class Config:
        orm_mode = True


# Definicja kategorii i ich limitów cenowych
CATEGORY_PRICE_LIMITS = {
    "Elektronika": {"min": 50.0, "max": 50000.0},
    "Książki": {"min": 5.0, "max": 500.0},
    "Odzież": {"min": 10.0, "max": 5000.0}
}

CategoryType = Literal["Elektronika", "Książki", "Odzież"]


# Product schemas
class ProductBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=20)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)
    category: CategoryType
    
    @field_validator('name')
    def validate_name(cls, v):
        # Sprawdzenie czy nazwa zawiera tylko litery i cyfry
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('Nazwa produktu może składać się tylko z liter i cyfr (bez spacji i znaków specjalnych)')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float, info: ValidationInfo) -> float:
        # Walidacja ceny względem kategorii
        if 'category' in info.data:
            category = info.data['category']
            limits = CATEGORY_PRICE_LIMITS.get(category)
            if limits:
                if v < limits['min']:
                    raise ValueError(
                        f"Cena dla kategorii '{category}' musi wynosić co najmniej {limits['min']} PLN"
                    )
                if v > limits['max']:
                    raise ValueError(
                        f"Cena dla kategorii '{category}' nie może przekraczać {limits['max']} PLN"
                    )
        return v

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductPartialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=20)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    category: Optional[CategoryType] = None
    
    @field_validator('name')
    def validate_name(cls, v):
        if v is not None:
            # Sprawdzenie czy nazwa zawiera tylko litery i cyfry
            if not re.match(r'^[a-zA-Z0-9]+$', v):
                raise ValueError('Nazwa produktu może składać się tylko z liter i cyfr (bez spacji i znaków specjalnych)')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float, info: ValidationInfo) -> float:
        # Walidacja ceny względem kategorii (jeśli podana)
        if v is not None and 'category' in info.data and info.data['category'] is not None:
            category = info.data['category']
            limits = CATEGORY_PRICE_LIMITS.get(category)
            if limits:
                if v < limits['min']:
                    raise ValueError(
                        f"Cena dla kategorii '{category}' musi wynosić co najmniej {limits['min']} PLN"
                    )
                if v > limits['max']:
                    raise ValueError(
                        f"Cena dla kategorii '{category}' nie może przekraczać {limits['max']} PLN"
                    )
        return v

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Product History schemas
class ProductHistoryBase(BaseModel):
    product_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    change_type: str

class ProductHistory(ProductHistoryBase):
    id: int
    changed_at: datetime

    class Config:
        from_attributes = True


# Banned Phrase schemas
class BannedPhraseBase(BaseModel):
    phrase: str = Field(..., min_length=1)

class BannedPhraseCreate(BannedPhraseBase):
    pass

class BannedPhrase(BannedPhraseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
