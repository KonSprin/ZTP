# product_repository.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from .. import models

class ProductRepository:
    def get_all(self, db: Session) -> List[models.Product]:
        return db.query(models.Product).all()

    def get_by_id(self, db: Session, id: int) -> Optional[models.Product]:
        return db.query(models.Product).filter(models.Product.id == id).first()
    
    def get_by_name(self, db: Session, name: str) -> Optional[models.Product]:
        """Pobiera produkt po nazwie (dla sprawdzenia unikalności)"""
        return db.query(models.Product).filter(models.Product.name == name).first()
    
    def create(self, db: Session, product: models.Product) -> models.Product:
        try:
            db.add(product)
            db.commit()
            db.refresh(product)
            return product
        except IntegrityError as e:
            db.rollback()
            if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                raise ValueError(f"Produkt o nazwie '{product.name}' już istnieje")
            raise
    
    def update(self, db: Session, id: int, product: models.Product) -> Optional[models.Product]:
        existing = db.query(models.Product).filter(models.Product.id == id).first()
        if not existing:
            return None
        
        try:
            for key, value in product.__dict__.items():
                if key != '_sa_instance_state' and key != 'id':
                    setattr(existing, key, value)
            
            db.commit()
            db.refresh(existing)
            return existing
        except IntegrityError as e:
            db.rollback()
            if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                raise ValueError(f"Produkt o nazwie '{product.name}' już istnieje")
            raise

    def patch(self, db: Session, id: int, data: dict) -> Optional[models.Product]:
        product = db.query(models.Product).filter(models.Product.id == id).first()
        if not product:
            return None
        
        try:
            for key, value in data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            
            db.commit()
            db.refresh(product)
            return product
        except IntegrityError as e:
            db.rollback()
            if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                if 'name' in data:
                    raise ValueError(f"Produkt o nazwie '{data['name']}' już istnieje")
            raise

    def delete(self, db: Session, id: int) -> dict:
        product = db.query(models.Product).filter(models.Product.id == id).first()
        if not product:
            return {"message": "Product doesn't exist", "code": 1}
        
        db.delete(product)
        db.commit()
        return {"message": "Product deleted", "code": 0}


class ProductHistoryRepository:
    def create(self, db: Session, history: models.ProductHistory) -> models.ProductHistory:
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    
    def get_by_product_id(self, db: Session, product_id: int) -> List[models.ProductHistory]:
        return db.query(models.ProductHistory)\
            .filter(models.ProductHistory.product_id == product_id)\
            .order_by(models.ProductHistory.changed_at.desc())\
            .all()
    
    def get_all(self, db: Session) -> List[models.ProductHistory]:
        return db.query(models.ProductHistory)\
            .order_by(models.ProductHistory.changed_at.desc())\
            .all()


class BannedPhraseRepository:
    def get_all(self, db: Session) -> List[models.BannedPhrase]:
        return db.query(models.BannedPhrase).all()
    
    def get_by_id(self, db: Session, id: int) -> Optional[models.BannedPhrase]:
        return db.query(models.BannedPhrase).filter(models.BannedPhrase.id == id).first()
    
    def get_by_phrase(self, db: Session, phrase: str) -> Optional[models.BannedPhrase]:
        return db.query(models.BannedPhrase).filter(models.BannedPhrase.phrase == phrase).first()
    
    def create(self, db: Session, phrase: models.BannedPhrase) -> models.BannedPhrase:
        db.add(phrase)
        db.commit()
        db.refresh(phrase)
        return phrase
    
    def delete(self, db: Session, id: int) -> dict:
        phrase = db.query(models.BannedPhrase).filter(models.BannedPhrase.id == id).first()
        if not phrase:
            return {"message": "Banned phrase doesn't exist", "code": 1}
        
        db.delete(phrase)
        db.commit()
        return {"message": "Banned phrase deleted", "code": 0}

