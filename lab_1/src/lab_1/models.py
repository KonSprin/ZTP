# models.py
from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, List
from .database import Base

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(default=0)
    category: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relacja do historii zmian
    history: Mapped[List["ProductHistory"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductHistory(Base):
    __tablename__ = "product_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    field_name: Mapped[str] = mapped_column(String)
    old_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_value: Mapped[str] = mapped_column(String)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    change_type: Mapped[str] = mapped_column(String)
    
    # Relacja do produktu
    product: Mapped["Product"] = relationship(back_populates="history")


class BannedPhrase(Base):
    __tablename__ = "banned_phrases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phrase: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
