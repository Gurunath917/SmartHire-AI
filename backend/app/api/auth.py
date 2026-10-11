"""
Authentication API routes.

POST /api/auth/register  — register a new candidate or recruiter
POST /api/auth/login     — login and receive JWT token
GET  /api/auth/me        — get current logged-in user (protected)
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.candidate_profile import CandidateProfile
from app.models.recruiter_profile import RecruiterProfile
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
)
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.dependencies import get_current_user
from app.utils.errors import conflict, unauthorized, bad_request
from app.utils.logger import logger

router = APIRouter()


# ── POST /api/auth/register ───────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=201,
    summary="Register a new user",
    description="Create a new CANDIDATE or RECRUITER account. ADMIN accounts are created manually.",
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    # 1. Check for duplicate email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise conflict("An account with this email already exists.")

    # 2. Hash password — never store plaintext
    hashed = hash_password(body.password)

    # 3. Create user
    user = User(
        email=body.email,
        hashed_password=hashed,
        full_name=body.full_name,
        user_role=body.role,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.flush()  # get user.id before committing

    # 4. Create matching profile (candidate or recruiter)
    if body.role == UserRole.CANDIDATE:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)
        logger.info("New CANDIDATE registered: {} (id={})", user.email, user.id)

    elif body.role == UserRole.RECRUITER:
        profile = RecruiterProfile(user_id=user.id)
        db.add(profile)
        logger.info("New RECRUITER registered: {} (id={})", user.email, user.id)

    db.commit()

    return MessageResponse(
        message=f"Account created successfully. Welcome to SmartHire AI, {user.full_name}!",
        success=True,
    )


# ── POST /api/auth/login ──────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns a JWT access token.",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    # 1. Find user by email
    user = db.query(User).filter(User.email == body.email).first()

    # 2. Verify password — use constant-time comparison via passlib
    #    Return the same error for wrong email OR wrong password (security best practice)
    if not user or not verify_password(body.password, user.hashed_password):
        raise unauthorized("Incorrect email or password.")

    # 3. Check account is active
    if not user.is_active:
        raise unauthorized("Your account has been deactivated. Please contact support.")

    # 4. Issue JWT
    expires_in_seconds = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = create_access_token(
        subject=str(user.id),
        role=user.user_role.value,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.info("User logged in: {} role={}", user.email, user.user_role.value)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.user_role,
    )


# ── GET /api/auth/me ──────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Returns the profile of the currently authenticated user.",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── POST /api/auth/logout ─────────────────────────────────────────────────────
@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout",
    description=(
        "Logout endpoint. Since JWTs are stateless, the client is responsible "
        "for deleting the token. This endpoint provides a clean API contract."
    ),
)
def logout(current_user: User = Depends(get_current_user)):
    logger.info("User logged out: {}", current_user.email)
    return MessageResponse(
        message="Logged out successfully. Please delete your token on the client side.",
        success=True,
    )
