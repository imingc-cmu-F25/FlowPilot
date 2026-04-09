import bcrypt
from pydantic import BaseModel
from app.user.emailAddress import EmailAddress


class UserPublic(BaseModel):
    name: str
    emails: list[EmailAddress]


class AuthResponse(BaseModel):
    ok: bool
    message: str
    user: UserPublic | None = None
    token: str | None = None


class UserCredentials(BaseModel):
    name: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    password: str
    email: str | None = None


class UserEmailUpdate(BaseModel):
    name: str
    address: str
    alias: str = ""


class User(BaseModel):
    name: str
    password: str
    emails: list[EmailAddress]

    def __str__(self):
        return f"User(name={self.name})"

    def get_user_name(self):
        return self.name

    def verify_password(self, password: str) -> bool:
        # use hashing to verify the password
        if not self.password:
            return False
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password.encode("utf-8"),
        )

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("ascii")

    def set_password(self, password: str) -> None:
        self.password = self.get_password_hash(password)
