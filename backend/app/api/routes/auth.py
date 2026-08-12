from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin, require_farmer
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    create_user_token,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_farmer(data: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = register_user(db, data)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=create_user_token(user))


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = authenticate_user(db, data.email, data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=create_user_token(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/test/farmer")
def farmer_test_endpoint(current_user: User = Depends(require_farmer)) -> dict[str, str]:
    return {
        "message": "Farmer access granted",
        "user_id": str(current_user.id),
        "role": current_user.role.value,
        "note": "Development/testing endpoint for RBAC verification",
    }


@router.get("/test/admin")
def admin_test_endpoint(current_user: User = Depends(require_admin)) -> dict[str, str]:
    return {
        "message": "Admin access granted",
        "user_id": str(current_user.id),
        "role": current_user.role.value,
        "note": "Development/testing endpoint for RBAC verification",
    }
