# banned_phrase_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from ..repositories.product_repository import BannedPhraseRepository
from .. import models, schemas

class BannedPhraseService:
    def __init__(self):
        self.repo = BannedPhraseRepository()
    
    def create_banned_phrase(self, db: Session, phrase_data: schemas.BannedPhraseCreate) -> models.BannedPhrase:
        """Dodaje nową zabronioną frazę"""
        # Sprawdzenie czy fraza już istnieje
        existing = self.repo.get_by_phrase(db, phrase_data.phrase)
        if existing:
            raise ValueError(f"Fraza '{phrase_data.phrase}' jest już na liście zabronionych")
        
        new_phrase = models.BannedPhrase(**phrase_data.dict())
        return self.repo.create(db, new_phrase)
    
    def get_banned_phrases(self, db: Session) -> List[models.BannedPhrase]:
        """Pobiera wszystkie zabronione frazy"""
        return self.repo.get_all(db)
    
    def get_banned_phrase(self, db: Session, id: int) -> Optional[models.BannedPhrase]:
        """Pobiera zabronioną frazę po ID"""
        return self.repo.get_by_id(db, id)
    
    def delete_banned_phrase(self, db: Session, id: int) -> dict:
        """Usuwa zabronioną frazę"""
        return self.repo.delete(db, id)
