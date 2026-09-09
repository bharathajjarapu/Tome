from fastapi import APIRouter, HTTPException, status

from tome.core.db import Db
from tome.core.security import create_token
from tome.schemas import Credentials, TokenOut, UserOut
from tome.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: Credentials, db: Db) -> UserOut:
    user = auth.register(db, body.email, body.password)
    if user is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenOut)
def login(body: Credentials, db: Db) -> TokenOut:
    userid = auth.authenticate(db, body.email, body.password)
    if userid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenOut(access_token=create_token(userid))
