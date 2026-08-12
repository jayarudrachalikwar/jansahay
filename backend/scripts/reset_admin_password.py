"""Reset the development admin account password from environment settings."""

import sys

from app.auth.security import hash_password
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.user import User, UserRole


def main() -> int:
    db = SessionLocal()
    try:
        admin = (
            db.query(User)
            .filter(
                User.email == settings.admin_email.lower(),
                User.role == UserRole.admin,
            )
            .first()
        )

        if admin is None:
            print(
                f"Admin account not found: {settings.admin_email}",
                file=sys.stderr,
            )
            return 1

        admin.password_hash = hash_password(settings.admin_password)
        db.commit()
        print(f"Admin password updated successfully: {admin.email}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
