"""Remove admin@hrms.dev user account and its associations from the database."""

import sys
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.hrms import RefreshTokenSession, User, UserRole


def main() -> int:
    db = SessionLocal()
    try:
        email = "admin@hrms.dev"
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if not user:
            print(f"Account '{email}' does not exist in the database.")
            return 0

        print(f"Found account '{email}' (ID: {user.id}). Removing...")
        db.query(RefreshTokenSession).filter(RefreshTokenSession.user_id == user.id).delete()
        db.query(UserRole).filter(UserRole.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        print(f"Account '{email}' deleted successfully.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Failed to remove '{email}': {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
