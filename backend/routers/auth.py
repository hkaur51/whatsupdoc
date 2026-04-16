"""Auth endpoints: signup, login, me. Issues JWTs used to gate /api/chat."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from database import get_database
from services.auth_service import (
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s'.-]{0,60}$")


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


async def _current_user_doc(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    db = get_database()
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    return await _current_user_doc(authorization)


def _public_user(doc: dict) -> dict:
    return {"id": doc["id"], "email": doc["email"], "name": doc.get("name")}


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest) -> AuthResponse:
    if not _NAME_RE.match(body.name.strip()):
        raise HTTPException(400, "Please enter a valid name.")
    db = get_database()
    email = body.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(409, "An account with that email already exists.")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": email,
        "name": body.name.strip(),
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = issue_token(user_id, email)
    return AuthResponse(token=token, user=_public_user(doc))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest) -> AuthResponse:
    db = get_database()
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid email or password.")
    token = issue_token(user["id"], email)
    return AuthResponse(token=token, user=_public_user(user))


@router.get("/me")
async def me(current=Depends(get_current_user)) -> dict:
    return current
