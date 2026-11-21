"""Idempotently create reusable built-in templates."""

from sqlalchemy import select

from app.database.session import get_session_factory
from app.models.email import EmailTemplate

DEFAULT_TEMPLATES = (
    {
        "template_key": "EMPLOYEE_INVITATION",
        "name": "Employee invitation",
        "subject": "Evolvus360 invited you to complete your profile",
        "body_text": (
            "Hello $employee_name,\n\nEvolvus360 has invited you to complete "
            "your profile. Please follow the link below to complete your profile:\n"
            "$invitation_link\n\n"
            "This link expires in $expiry_hours hours."
        ),
        "body_html": (
            "<p>Hello $employee_name,</p><p>Evolvus360 has invited you to complete "
            "your profile. Please follow the link below to complete your profile:</p>"
            '<p><a href="$invitation_link">Complete your profile</a></p>'
            "<p>This link expires in $expiry_hours hours.</p>"
        ),
        "description": "Invitation link for employee onboarding.",
        "required_variables": [
            "employee_name",
            "invitation_link",
            "expiry_hours",
        ],
    },
    {
        "template_key": "PASSWORD_RESET",
        "name": "Password reset",
        "subject": "Reset your Evolvus360 password",
        "body_text": "Use this single-use link to reset your password: $reset_link",
        "body_html": (
            '<p>Use this single-use <a href="$reset_link">password reset link</a>.</p>'
        ),
        "description": "Single-use password reset email.",
        "required_variables": ["reset_link"],
    },
    {
        "template_key": "WELCOME_EMAIL",
        "name": "Welcome",
        "subject": "Welcome to $company_name, $employee_name",
        "body_text": "Hello $employee_name, welcome to $company_name.",
        "body_html": "<p>Hello $employee_name, welcome to $company_name.</p>",
        "description": "Welcome email for newly onboarded employees.",
        "required_variables": ["employee_name", "company_name"],
    },
    {
        "template_key": "EMPLOYEE_PROFILE_SUBMITTED",
        "name": "Employee profile submitted",
        "subject": "Employee profile submitted: $employee_name",
        "body_text": "$employee_name submitted an employee profile for review.",
        "body_html": "<p>$employee_name submitted an employee profile for review.</p>",
        "description": "HR notification when employee onboarding is submitted.",
        "required_variables": ["employee_name"],
    },
    {
        "template_key": "EMPLOYEE_PROFILE_APPROVED",
        "name": "Employee profile approved",
        "subject": "Your Evolvus360 profile is approved",
        "body_text": "Hello $employee_name, your profile at $company_name is approved.",
        "body_html": (
            "<p>Hello $employee_name, your profile at $company_name is approved.</p>"
        ),
        "description": "Employee notification after HR profile approval.",
        "required_variables": ["employee_name", "company_name"],
    },
    {
        "template_key": "GENERAL_NOTIFICATION",
        "name": "General notification",
        "subject": "$subject_line",
        "body_text": "$message_text",
        "body_html": "<p>$message_text</p>",
        "description": "Generic text-only internal notification.",
        "required_variables": ["subject_line", "message_text"],
        "allow_custom_subject": True,
    },
)


def main() -> int:
    with get_session_factory()() as db:
        try:
            for data in DEFAULT_TEMPLATES:
                existing = db.scalar(
                    select(EmailTemplate).where(
                        EmailTemplate.template_key == data["template_key"]
                    )
                )
                if existing is None:
                    db.add(EmailTemplate(**data))
                elif data["template_key"] == "EMPLOYEE_INVITATION":
                    for field, value in data.items():
                        setattr(existing, field, value)
            db.commit()
        except BaseException:
            db.rollback()
            raise
    print(f"Seeded or confirmed {len(DEFAULT_TEMPLATES)} templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
