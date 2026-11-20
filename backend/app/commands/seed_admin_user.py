"""Idempotently seed default Super Admin user and master roles."""

import sys
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.hrms import User
from app.services.auth_service import create_super_admin, seed_master_roles


def main() -> int:
    db = SessionLocal()
    try:
        print("1. Seeding master roles...")
        for code, name, role_id, created in seed_master_roles(db):
            status = "CREATED" if created else "EXISTS"
            print(f"   [{status}] {code}: {name} ({role_id})")

        email = "admin@hrms.dev"
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            print(f"2. Super admin '{email}' already exists (ID: {existing.id}).")
            return 0

        user = create_super_admin(
            db,
            email=email,
            first_name="Super",
            last_name="Admin",
            password="Admin@Evolvus360!",
        )
        print(f"2. Created Super Admin '{user.email}' with password 'Admin@Evolvus360!' (ID: {user.id})")
        return 0
    except Exception as exc:
        print(f"Failed to seed admin user: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
