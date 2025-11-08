# users.py
from fastapi import APIRouter, Depends, HTTPException
from .. import schemas, database
from ..services.user_service import UserService

router = APIRouter(prefix="/users")
service = UserService()

@router.get("", response_model=list[schemas.User])
def get_users(db = Depends(database.get_db)):
    return service.get_users(db)

@router.get("/{id}", response_model=schemas.User)
def get_user(id: int, db = Depends(database.get_db)):
    user = service.get_user(db, id)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@router.post("", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db=Depends(database.get_db)):
    try:
        return service.create_user(db, user)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

@router.put("/{id}", response_model=schemas.User)
def update_user(id: int, updated: schemas.UserCreate, db=Depends(database.get_db)):
    user = service.update_user(db, updated, id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
    
@router.patch("/{id}", response_model=schemas.User)
def patch_user(id: int, data: dict, db=Depends(database.get_db)):
    user = service.patch_user(db, data, id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
    
@router.delete("/{id}")
def delete_user(id: int, db=Depends(database.get_db)):
    messege = service.delete_user(db, id)
    if messege["code"] == 1:
        raise HTTPException(404, "User not found")
    return messege
