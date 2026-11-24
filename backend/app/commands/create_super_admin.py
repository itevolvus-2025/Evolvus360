"""Create or update a global Super Admin with full access to all system modules."""

import argparse
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import DBAPIError

from app.core.security import normalize_email, validate_password_strength
from app.database.session import SessionLocal
from app.services.auth_service import SUPER_ADMIN_PERMISSIONS, create_super_admin


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or configure a Super Admin user with access to all modules."
    )
    parser.add_argument("--email", help="Super Admin email address", default=None)
    parser.add_argument("--password", help="Super Admin password (min 8 chars with upper, lower, number, symbol)", default=None)
    parser.add_argument("--first-name", help="First name", default=None)
    parser.add_argument("--last-name", help="Last name", default=None)

    args = parser.parse_args()

    # If flags are provided via CLI, use them; otherwise, prompt interactively
    if args.email:
        raw_email = args.email
    else:
        raw_email = input("Email: ").strip()

    try:
        email = normalize_email(TypeAdapter(EmailStr).validate_python(raw_email))
    except ValidationError:
        print("A valid email address is required.", file=sys.stderr)
        return 1

    first_name = (args.first_name or "").strip()
    if not first_name:
        first_name = input("First name: ").strip()

    last_name = (args.last_name or "").strip()
    if not last_name:
        last_name = input("Last name: ").strip()

    if not first_name or not last_name:
        print("First name and last name are required.", file=sys.stderr)
        return 1

    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1

    try:
        validate_password_strength(password)
    except ValueError as exc:
        print(f"Password requirement error: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = create_super_admin(db, email, first_name, last_name, password)
        print("\n=======================================================")
        print(f" SUCCESS: Super Admin user configured successfully!")
        print("=======================================================")
        print(f" User ID    : {user.id}")
        print(f" Email      : {user.email}")
        print(f" Name       : {user.first_name} {user.last_name}")
        print(f" Role       : SUPER_ADMIN (Super Admin)")
        print(f" Status     : {user.account_status}")
        print(" All Module Access Granted:")
        for perm in [p for p in SUPER_ADMIN_PERMISSIONS if p not in {"*", "all"}]:
            print(f"   [✓] {perm}")
        print("=======================================================\n")
        return 0
    except (ValueError, LookupError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except DBAPIError as exc:
        detail = str(getattr(exc, "orig", exc)).strip()
        sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
        if sqlstate:
            print(
                f"Super Admin creation failed ({type(exc).__name__}, "
                f"SQLSTATE {sqlstate}): {detail}",
                file=sys.stderr,
            )
        else:
            print(
                f"Super Admin creation failed ({type(exc).__name__}): {detail}",
                file=sys.stderr,
            )
        return 1
    except Exception as exc:
        print(f"Super Admin creation failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1
    finally:
        password = ""
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
