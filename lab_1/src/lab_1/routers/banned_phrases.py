# banned_phrases.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .. import schemas, database
from ..services.banned_phrase_service import BannedPhraseService

router = APIRouter(prefix="/banned-phrases", tags=["banned-phrases"])
service = BannedPhraseService()

@router.get("", response_model=List[schemas.BannedPhrase])
def get_banned_phrases(db = Depends(database.get_db)):
    """Pobiera listę wszystkich zabronionych fraz"""
    return service.get_banned_phrases(db)

@router.get("/{id}", response_model=schemas.BannedPhrase)
def get_banned_phrase(id: int, db = Depends(database.get_db)):
    """Pobiera szczegóły zabronionej frazy po ID"""
    phrase = service.get_banned_phrase(db, id)
    if not phrase:
        raise HTTPException(404, "Banned phrase not found")
    return phrase

@router.post("", response_model=schemas.BannedPhrase, status_code=201)
def create_banned_phrase(phrase: schemas.BannedPhraseCreate, db=Depends(database.get_db)):
    """Dodaje nową zabronioną frazę"""
    try:
        return service.create_banned_phrase(db, phrase)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

@router.delete("/{id}")
def delete_banned_phrase(id: int, db=Depends(database.get_db)):
    """Usuwa zabronioną frazę"""
    result = service.delete_banned_phrase(db, id)
    if result["code"] == 1:
        raise HTTPException(404, "Banned phrase not found")
    return result
