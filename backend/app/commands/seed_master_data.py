"""Idempotently seed stable system role codes without replacing existing IDs."""

import sys

from app.database.session import SessionLocal
from app.services.auth_service import seed_master_roles


def main() -> int:
    print("Seeding Evolvus360 master data...\n")
    db = SessionLocal()
    try:
        for _code, name, role_id, created in seed_master_roles(db):
            print(f"[{'CREATED' if created else 'EXISTS'}] {name} (ID: {role_id})")
        print("\nMaster data seeding completed successfully.")
        return 0
    except Exception as exc:
        print(f"Master data seeding failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
