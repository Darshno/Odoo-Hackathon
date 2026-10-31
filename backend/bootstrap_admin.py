import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, validate_password_policy
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> int:
    if not all([settings.bootstrap_admin_name, settings.bootstrap_admin_email, settings.bootstrap_admin_password]):
        print("Set BOOTSTRAP_ADMIN_NAME, BOOTSTRAP_ADMIN_EMAIL, and BOOTSTRAP_ADMIN_PASSWORD before running this command.")
        return 1
    validate_password_policy(settings.bootstrap_admin_password)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.role == UserRole.ADMIN)):
            print("An administrator already exists; refusing to create another bootstrap administrator.")
            return 1
        email = settings.bootstrap_admin_email.lower()
        if db.scalar(select(User).where(User.email == email)):
            print("That email is already registered; refusing to change its role through bootstrap.")
            return 1
        user = User(full_name=settings.bootstrap_admin_name, email=email, password_hash=hash_password(settings.bootstrap_admin_password), role=UserRole.ADMIN)
        db.add(user)
        db.commit()
        print(f"Created the first administrator: {email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
