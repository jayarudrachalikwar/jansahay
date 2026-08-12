from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import UserRegister


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def register_user(db: Session, data: UserRegister) -> User:
    normalized_email = data.email.lower()

    if get_user_by_email(db, normalized_email) is not None:
        raise EmailAlreadyRegisteredError("Email is already registered")

    user = User(
        full_name=data.full_name.strip(),
        email=normalized_email,
        phone_number=data.phone_number.strip() if data.phone_number else None,
        password_hash=hash_password(data.password),
        role=UserRole.farmer,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email.lower())
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.is_active:
        raise InvalidCredentialsError("Account is inactive")

    return user


def create_user_token(user: User) -> str:
    return create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value,
            "email": user.email,
        }
    )


def create_admin_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    phone_number: str | None = None,
) -> User:
    normalized_email = email.lower()

    if get_user_by_email(db, normalized_email) is not None:
        raise EmailAlreadyRegisteredError("Email is already registered")

    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        phone_number=phone_number.strip() if phone_number else None,
        password_hash=hash_password(password),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
