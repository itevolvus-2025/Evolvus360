"""Create the initial global Super Admin through an interactive trusted CLI."""

import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.security import normalize_email, validate_password_strength
from app.database.session import SessionLocal
from app.services.auth_service import create_super_admin


def main() -> int:
    try:
        email = normalize_email(TypeAdapter(EmailStr).validate_python(input("Email: ")))
    except ValidationError:
        print("A valid email address is required.", file=sys.stderr)
        return 1
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    try:
        validate_password_strength(password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not first_name or not last_name:
        print("First name and last name are required.", file=sys.stderr)
        return 1
    db = SessionLocal()
    try:
        user = create_super_admin(db, email, first_name, last_name, password)
        print(f"Super Admin created: {user.email} (ID: {user.id})")
        return 0
    except (ValueError, LookupError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Super Admin creation failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    finally:
        password = confirm = ""
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
