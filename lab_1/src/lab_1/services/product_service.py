# product_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from ..repositories.product_repository import ProductRepository, ProductHistoryRepository, BannedPhraseRepository
from .. import models, schemas

class ProductService:
    def __init__(self):
        self.repo = ProductRepository()
        self.history_repo = ProductHistoryRepository()
        self.banned_repo = BannedPhraseRepository()
    
    def _check_banned_phrases(self, db: Session, name: str) -> None:
        """Sprawdza czy nazwa produktu zawiera zabronione frazy"""
        banned_phrases = self.banned_repo.get_all(db)
        name_lower = name.lower()
        
        for banned in banned_phrases:
            if banned.phrase.lower() in name_lower:
                raise ValueError(f"Nazwa produktu zawiera zabronioną frazę: '{banned.phrase}'")
    
    def _validate_price_for_category(self, price: float, category: str) -> None:
        """Waliduje cenę względem kategorii"""
        price_limits = schemas.CATEGORY_PRICE_LIMITS.get(category)
        if not price_limits:
            raise ValueError(f"Nieznana kategoria: '{category}'")
        
        if price < price_limits['min']:
            raise ValueError(
                f"Cena dla kategorii '{category}' musi wynosić co najmniej {price_limits['min']} PLN"
            )
        if price > price_limits['max']:
            raise ValueError(
                f"Cena dla kategorii '{category}' nie może przekraczać {price_limits['max']} PLN"
            )
    
    def _check_name_uniqueness(self, db: Session, name: str, exclude_id: Optional[int] = None) -> None:
        """Sprawdza czy nazwa produktu jest unikalna"""
        existing = self.repo.get_by_name(db, name)
        if existing and (exclude_id is None or existing.id != exclude_id):
            raise ValueError(f"Produkt o nazwie '{name}' już istnieje")

    def _log_history(self, db: Session, product_id: int, field_name: str, 
                     old_value: Optional[str], new_value: str, change_type: str) -> None:
        """Zapisuje historię zmian w produkcie"""
        history = models.ProductHistory(
            product_id=product_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type
        )
        self.history_repo.create(db, history)
    
    def _log_product_creation(self, db: Session, product: models.Product) -> None:
        """Zapisuje historię utworzenia produktu"""
        fields = {
            'name': product.name,
            'description': product.description or '',
            'price': str(product.price),
            'quantity': str(product.quantity),
            'category': product.category
        }
        
        for field_name, value in fields.items():
            self._log_history(db, product.id, field_name, None, value, 'created')
    
    def _log_product_update(self, db: Session, old_product: models.Product, new_data: dict) -> None:
        """Zapisuje historię aktualizacji produktu"""
        for field_name, new_value in new_data.items():
            if hasattr(old_product, field_name):
                old_value = getattr(old_product, field_name)
                if old_value != new_value:
                    self._log_history(
                        db, 
                        old_product.id,
                        field_name, 
                        str(old_value) if old_value is not None else None, 
                        str(new_value), 
                        'updated'
                    )
    
    def create_product(self, db: Session, product_data: schemas.ProductCreate) -> models.Product:
        """Tworzy nowy produkt"""
        # Sprawdzenie zabronionych fraz
        self._check_banned_phrases(db, product_data.name)
        
        # Sprawdzenie unikalności nazwy
        self._check_name_uniqueness(db, product_data.name)
        
        # Walidacja ceny dla kategorii (dodatkowa walidacja na poziomie serwisu)
        self._validate_price_for_category(product_data.price, product_data.category)
        
        # Utworzenie produktu
        new_product = models.Product(**product_data.dict())
        created_product = self.repo.create(db, new_product)
        
        # Zapisanie historii utworzenia
        self._log_product_creation(db, created_product)
        
        return created_product
    
    def get_products(self, db: Session) -> List[models.Product]:
        """Pobiera wszystkie produkty"""
        return self.repo.get_all(db)
    
    def get_product(self, db: Session, id: int) -> Optional[models.Product]:
        """Pobiera produkt po ID"""
        return self.repo.get_by_id(db, id)
    
    def update_product(self, db: Session, id: int, product_data: schemas.ProductUpdate) -> Optional[models.Product]:
        """Aktualizuje cały produkt (PUT)"""
        # Sprawdzenie czy produkt istnieje
        existing = self.repo.get_by_id(db, id)
        if not existing:
            return None
        
        # Sprawdzenie zabronionych fraz
        self._check_banned_phrases(db, product_data.name)
        
        # Sprawdzenie unikalności nazwy (pomijając bieżący produkt)
        self._check_name_uniqueness(db, product_data.name, exclude_id=id)
        
        # Walidacja ceny dla kategorii
        self._validate_price_for_category(product_data.price, product_data.category)
        
        # Zapisanie starego stanu przed aktualizacją
        self._log_product_update(db, existing, product_data.dict())
        
        # Aktualizacja
        new_product = models.Product(**product_data.dict())
        return self.repo.update(db, id, new_product)
    
    def patch_product(self, db: Session, id: int, data: dict) -> Optional[models.Product]:
        """Częściowa aktualizacja produktu (PATCH)"""
        # Sprawdzenie czy produkt istnieje
        existing = self.repo.get_by_id(db, id)
        if not existing:
            return None
        
        # Sprawdzenie zabronionych fraz jeśli nazwa jest aktualizowana
        if 'name' in data:
            self._check_banned_phrases(db, data['name'])
            self._check_name_uniqueness(db, data['name'], exclude_id=id)
        
        # Walidacja ceny dla kategorii
        # Jeśli zmienia się kategoria lub cena, musimy sprawdzić zgodność
        if 'price' in data or 'category' in data:
            new_price = data.get('price', existing.price)
            new_category = data.get('category', existing.category)
            self._validate_price_for_category(new_price, new_category)
        
        # Zapisanie historii zmian
        self._log_product_update(db, existing, data)
        
        # Aktualizacja
        return self.repo.patch(db, id, data)
    
    def delete_product(self, db: Session, id: int) -> dict:
        """Usuwa produkt"""
        # Sprawdzenie czy produkt istnieje przed usunięciem
        product = self.repo.get_by_id(db, id)
        if product:
            # Zapisanie historii usunięcia
            self._log_history(db, product.id, 'deleted', None, 'Product deleted', 'deleted')
        
        return self.repo.delete(db, id)
    
    def get_product_history(self, db: Session, product_id: int) -> List[models.ProductHistory]:
        """Pobiera historię zmian produktu"""
        return self.history_repo.get_by_product_id(db, product_id)
    
    def get_all_history(self, db: Session) -> List[models.ProductHistory]:
        """Pobiera całą historię zmian wszystkich produktów"""
        return self.history_repo.get_all(db)
