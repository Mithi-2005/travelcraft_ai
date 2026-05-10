from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    AuthSessionResponse,
    DestinationSuggestion,
    GenerateTripRequest,
    LoginRequest,
    MessageResponse,
    PastTrip,
    RegisterRequest,
    TripPlanResponse,
    UpdateMemoryRequest,
    UserMemory,
)
from app.security import clear_auth_cookie, create_session_token, get_current_user, set_auth_cookie
from app.services.auth_service import AuthService
from app.services.destination_service import DestinationService
from app.services.memory_service import MemoryService
from app.services.planner_service import PlannerService


memory_service = MemoryService()
planner_service = PlannerService()
auth_service = AuthService()
destination_service = DestinationService()

app = FastAPI(
    title="TravelCraft AI API",
    version="1.0.0",
    description="Backend for personalized itinerary generation using live research, LLM planning, and memory persistence.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/destination-suggestions", response_model=list[DestinationSuggestion])
async def get_destination_suggestions(q: str = "", limit: int = 6) -> list[DestinationSuggestion]:
    return destination_service.search(q, limit)


@app.post("/auth/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    user = auth_service.register_user(db, payload)
    set_auth_cookie(response, create_session_token(user.id))
    return AuthSessionResponse(user=auth_service.serialize_user(user))


@app.post("/auth/login", response_model=AuthSessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    user = auth_service.authenticate_user(db, payload)
    set_auth_cookie(response, create_session_token(user.id))
    return AuthSessionResponse(user=auth_service.serialize_user(user))


@app.post("/auth/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    clear_auth_cookie(response)
    return MessageResponse(message="Logged out successfully.")


@app.get("/auth/me", response_model=AuthSessionResponse)
async def get_me(user=Depends(get_current_user)) -> AuthSessionResponse:
    return AuthSessionResponse(user=auth_service.serialize_user(user))


@app.get("/user-memory", response_model=UserMemory)
async def get_user_memory(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> UserMemory:
    return memory_service.load_memory(db, user)


@app.get("/trips/{trip_id}", response_model=PastTrip)
async def get_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> PastTrip:
    trip = memory_service.get_trip(db, user, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    return trip


@app.post("/update-memory", response_model=UserMemory)
async def update_user_memory(
    payload: UpdateMemoryRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> UserMemory:
    return memory_service.update_memory(db, user, payload)


@app.post("/generate-trip", response_model=TripPlanResponse)
async def generate_trip(
    payload: GenerateTripRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> TripPlanResponse:
    memory = memory_service.load_memory(db, user)
    plan = await planner_service.generate_trip(payload, memory)
    memory_service.store_generated_trip(db, user, payload, plan)
    return plan
