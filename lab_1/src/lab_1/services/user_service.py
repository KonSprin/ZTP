# user_service.py
from ..repositories.user_repository import UserRepository
from .. import models

class UserService:
    def __init__(self):
        self.repo = UserRepository()
    
    def create_user(self, db, user_data):
        if not user_data.email.endswith("@example.com"):
            raise ValueError("Email musi pochodzié¢ z domeny @example.com")
        new_user = models.User(**user_data.dict())
        return self.repo.create(db, new_user)
    
    def get_users(self, db):
        return self.repo.get_all(db)
    
    def get_user(self, db, id: int):
        return self.repo.get_by_id(db, id)

    def update_user(self, db, updated, id: int):
        return self.repo.update(db=db, id=id, updated=updated)
    
    def patch_user(self, db, data, id: int):
        return self.repo.patch(db=db, id=id, data=data)
    
    def delete_user(self, db, id: int):
        return self.repo.delete(db=db, id=id)
