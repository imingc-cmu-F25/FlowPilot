from app.db.schema import UserORM, UserSessionORM
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> UserORM | None:
        return self.db.get(UserORM, name)

    def create(
        self, name: str, password_hash: str, emails: list | None = None
    ) -> UserORM:
        user = UserORM(name=name, password_hash=password_hash, emails=emails)
        self.db.add(user)
        return user

    def get_all_users(self) -> list[UserORM]:
        return list(self.db.scalars(select(UserORM).order_by(UserORM.name)).all())

    def update_emails(self, name: str, emails: list) -> UserORM | None:
        existing_user = self.db.get(UserORM, name)
        if existing_user:
            existing_user.emails = emails
            self.db.commit()
            return existing_user
        return None
        

    def create_session(self, token: str, user_name: str) -> UserSessionORM:
        session = UserSessionORM(token=token, user_name=user_name)
        self.db.add(session)
        return session