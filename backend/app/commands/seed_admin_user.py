"""Idempotently seed master roles."""

import sys
from app.database.session import SessionLocal
from app.services.auth_service import seed_master_roles


def main() -> int:
    db = SessionLocal()
    try:
        print("1. Seeding master roles...")
        for code, name, role_id, created in seed_master_roles(db):
            status = "CREATED" if created else "EXISTS"
            print(f"   [{status}] {code}: {name} ({role_id})")
        return 0
    except Exception as exc:
        print(f"Failed to seed master roles: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
