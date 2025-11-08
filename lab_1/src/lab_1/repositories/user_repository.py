# user_repository.py
from sqlalchemy.orm import Session
from .. import models, schemas

class UserRepository:
    def get_all(self, db: Session):
        return db.query(models.User).all()

    def get_by_id(self, db: Session, id: int):
        return db.query(models.User).filter(models.User.id == id).first()
    
    def create(self, db: Session, user: models.User):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def update(self, db: Session, id: int, updated: schemas.UserCreate):
        user = db.query(models.User).filter(models.User.id == id).first()
        user.name = updated.name # type: ignore
        user.email = updated.email # type: ignore
        db.commit()
        db.refresh(user)
        return user

    def patch(self, db: Session, id: int, data: dict):
        user = db.query(models.User).filter(models.User.id == id).first()
        for key, value in data.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user

    def delete(self, db: Session, id: int):
        user = db.query(models.User).filter(models.User.id == id).first()
        if not user:
            return {"message": "User doesn't exists",
                    "code": 1}
        db.delete(user)
        db.commit()
        return {"message": "User deleted", 
                "code": 0}
