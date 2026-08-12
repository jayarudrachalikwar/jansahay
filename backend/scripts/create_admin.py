"""Create the initial development admin account if one does not already exist."""

import sys

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import EmailAlreadyRegisteredError, create_admin_user, get_user_by_email


def main() -> int:
    if settings.admin_password == "change-admin-password":
        print(
            "Warning: using the default ADMIN_PASSWORD. "
            "Set ADMIN_PASSWORD in your environment before running in production.",
            file=sys.stderr,
        )

    db = SessionLocal()
    try:
        existing_admin = (
            db.query(User).filter(User.role == UserRole.admin).first()
        )
        if existing_admin is not None:
            print(f"Admin account already exists: {existing_admin.email}")
            return 0

        if get_user_by_email(db, settings.admin_email) is not None:
            print(
                f"Cannot create admin: email already in use ({settings.admin_email})",
                file=sys.stderr,
            )
            return 1

        user = create_admin_user(
            db,
            full_name=settings.admin_full_name,
            email=settings.admin_email,
            password=settings.admin_password,
            phone_number=None,
        )
        print(f"Admin account created: {user.email}")
        return 0
    except EmailAlreadyRegisteredError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
