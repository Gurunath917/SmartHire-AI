"""
FastAPI dependencies for authentication and role-based access control.

Usage in route handlers:
    # Any authenticated user
    @router.get("/me")
    def me(current_user: User = Depends(get_current_user)):
        ...

    # Specific role only
    @router.post("/jobs")
    def create_job(current_user: User = Depends(require_role(UserRole.RECRUITER))):
        ...

    # Multiple roles allowed
    @router.get("/dashboard")
    def dashboard(current_user: User = Depends(require_roles([UserRole.RECRUITER, UserRole.ADMIN]))):
        ...
"""
from typing import Callable, Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.utils.security import decode_access_token
from app.utils.errors import unauthorized, forbidden

# HTTPBearer extracts the token from the Authorization: Bearer <token> header
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the JWT, verify the user exists and is active.
    Raises 401 for missing/invalid token, 401 for inactive user.
    """
    if credentials is None:
        raise unauthorized("Authentication required. Please provide a Bearer token.")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise unauthorized("Invalid token: missing subject claim.")
    except JWTError:
        raise unauthorized("Invalid or expired token. Please log in again.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise unauthorized("User account not found.")
    if not user.is_active:
        raise unauthorized("User account is deactivated.")

    return user


def require_role(role: UserRole) -> Callable:
    """
    Dependency factory — requires the current user to have a specific role.

    Example:
        Depends(require_role(UserRole.RECRUITER))
    """
    def _require_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.user_role != role:
            raise forbidden(
                f"Access denied. This endpoint requires the '{role.value}' role."
            )
        return current_user
    return _require_role


def require_roles(roles: list[UserRole]) -> Callable:
    """
    Dependency factory — requires the current user to have one of the given roles.

    Example:
        Depends(require_roles([UserRole.RECRUITER, UserRole.ADMIN]))
    """
    def _require_roles(current_user: User = Depends(get_current_user)) -> User:
        if current_user.user_role not in roles:
            allowed = ", ".join(r.value for r in roles)
            raise forbidden(
                f"Access denied. This endpoint requires one of: [{allowed}]."
            )
        return current_user
    return _require_roles


# ── Convenience shorthand dependencies ───────────────────────────────────────
def get_current_candidate(current_user: User = Depends(get_current_user)) -> User:
    """Shorthand — only allows CANDIDATE role."""
    if current_user.user_role != UserRole.CANDIDATE:
        raise forbidden("Access denied. Candidates only.")
    return current_user


def get_current_recruiter(current_user: User = Depends(get_current_user)) -> User:
    """Shorthand — only allows RECRUITER role."""
    if current_user.user_role != UserRole.RECRUITER:
        raise forbidden("Access denied. Recruiters only.")
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Shorthand — only allows ADMIN role."""
    if current_user.user_role != UserRole.ADMIN:
        raise forbidden("Access denied. Admins only.")
    return current_user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Returns the current user if a valid token is provided, else None.
    Does NOT raise 401 — used for public endpoints that optionally show
    extra data when the user is authenticated.
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user if (user and user.is_active) else None
    except Exception:
        return None
