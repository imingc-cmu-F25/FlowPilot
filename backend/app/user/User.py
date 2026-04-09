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
