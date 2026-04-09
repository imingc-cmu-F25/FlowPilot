from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, NotFoundError, AuthenticationError, ValidationError
from app.db.session import get_db
from app.user.emailAddress import EmailAddress
from app.user.service import UserService
from app.user.user import (
    AuthResponse,
    RegisterRequest,
    UserCredentials,
    UserEmailUpdate,
    UserPublic,
)

router = APIRouter()

@router.post("/register", response_model=AuthResponse, tags=["auth"])
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return UserService(db).register(body.name, body.password, body.email)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)

@router.post("/login", response_model=tuple[AuthResponse, str], tags=["auth"])
def login(user: UserCredentials, db: Session = Depends(get_db)) -> tuple[AuthResponse, str]:
    try:
        return UserService(db).login(user.name, user.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.get("/users", response_model=list[UserPublic], tags=["auth"])
def get_all_users(db: Session = Depends(get_db)) -> list[UserPublic]:
    try:
        return UserService(db).get_all_users()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message)

@router.put("/users/emails", response_model=UserPublic, tags=["auth"])
def update_email(body: UserEmailUpdate, db: Session = Depends(get_db)) -> UserPublic:
    try:
        return UserService(db).update_email(
            body.name,
            EmailAddress(address=body.address, alias=body.alias),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message)