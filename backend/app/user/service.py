import secrets

import bcrypt
from app.core.exceptions import AuthenticationError, DuplicateError, NotFoundError
from app.user.emailAddress import EmailAddress
from app.user.repo import UserRepository
from app.user.user import AuthResponse, UserPublic
from sqlalchemy.orm import Session


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def register(
        self, name: str, password: str, email: str | None = None
    ) -> AuthResponse:
        if self.repo.get_by_name(name):
            raise DuplicateError("Username already registered")

        password_hash = _hash_password(password)
        initial_emails: list | None = None
        if email:
            initial_emails = [{"address": email, "alias": ""}]
        user_orm = self.repo.create(name, password_hash, initial_emails)
        emails = [
            EmailAddress(address=e["address"], alias=e.get("alias", ""))
            for e in (user_orm.emails or [])
        ]
        return AuthResponse(
            ok=True,
            message="Registration successful",
            user=UserPublic(name=name, emails=emails),
            token=None,
        )

    def login(self, name: str, password: str) -> AuthResponse:
        user = self.repo.get_by_name(name)

        if not user:
            raise AuthenticationError("Invalid username or password")

        if not _verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        token = secrets.token_urlsafe(32)
        self.repo.create_session(token, name)

        emails = [
            EmailAddress(address=e["address"], alias=e.get("alias", ""))
            for e in (user.emails or [])
        ]
        return AuthResponse(
            ok=True,
            message="Login successful",
            user=UserPublic(name=name, emails=emails),
            token=token,
        )

    def get_all_users(self) -> list[UserPublic]:
        rows = self.repo.get_all_users()
        ret = []
        for row in rows: 
            emails = []
            for email in row.emails or []: 
                emails.append(EmailAddress(address=email["address"], alias=email["alias"]))
            ret.append(UserPublic(name=row.name, emails=emails))
        return ret

    def delete_email(self, name: str, address: str) -> UserPublic:
        user = self.repo.get_by_name(name)
        if not user:
            raise NotFoundError("User not found")
        updated_list = [e for e in (user.emails or []) if e["address"] != address]
        updated = self.repo.update_emails(name, updated_list)
        if not updated:
            raise NotFoundError("User not found")
        emails = [
            EmailAddress(address=e["address"], alias=e.get("alias", ""))
            for e in (updated.emails or [])
        ]
        return UserPublic(name=name, emails=emails)

    def edit_email(self, name: str, old_address: str, new_email: EmailAddress) -> UserPublic:
        user = self.repo.get_by_name(name)
        if not user:
            raise NotFoundError("User not found")
        current = list(user.emails or [])
        updated_list = [
            {"address": new_email.address, "alias": new_email.alias}
            if e["address"] == old_address
            else e
            for e in current
        ]
        updated = self.repo.update_emails(name, updated_list)
        if not updated:
            raise NotFoundError("User not found")
        emails = [
            EmailAddress(address=e["address"], alias=e.get("alias", ""))
            for e in (updated.emails or [])
        ]
        return UserPublic(name=name, emails=emails)

    def update_email(self, name: str, email: EmailAddress) -> UserPublic:
        user = self.repo.get_by_name(name)

        if not user:
            raise NotFoundError("User not found")

        current = list(user.emails or [])
        current.append({"address": email.address, "alias": email.alias})
        updated = self.repo.update_emails(name, current)
        if not updated:
            raise NotFoundError("User not found")
        emails = [
            EmailAddress(address=e["address"], alias=e.get("alias", ""))
            for e in (updated.emails or [])
        ]
        return UserPublic(name=name, emails=emails)
