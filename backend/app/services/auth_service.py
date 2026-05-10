from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import User, UserPreference
from app.models import AuthUserResponse, LoginRequest, RegisterRequest
from app.security import hash_password, verify_password


class AuthService:
    def register_user(self, db: Session, payload: RegisterRequest) -> User:
        normalized_email = payload.email.lower()
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists.",
            )

        user = User(
            email=normalized_email,
            password_hash=hash_password(payload.password),
            name=payload.name.strip(),
        )
        user.preference = UserPreference(
            bio="",
            home_airport="",
            budget_min=None,
            budget_max=None,
            travel_style="balanced",
            interests=[],
            trip_mood="relaxed",
            preferred_transport="mixed",
            accommodation_type="mixed",
            language_preferences=[],
            dietary_preferences=[],
            accessibility_needs={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, db: Session, payload: LoginRequest) -> User:
        normalized_email = payload.email.lower()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        return user

    def serialize_user(self, user: User) -> AuthUserResponse:
        return AuthUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
        )
