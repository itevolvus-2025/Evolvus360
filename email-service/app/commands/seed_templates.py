"""Idempotently create reusable built-in templates (Evolvus 360 blue/white theme)."""

from sqlalchemy import select

from app.database.session import get_session_factory
from app.models.email import EmailTemplate

BLUE = "#2563EB"
GREEN = "#5BAA2D"
INK = "#0F172A"
MUTED = "#64748B"
BG = "#F3F6FC"
BORDER = "#E2E8F0"
FONT = "'Poppins','Segoe UI',Helvetica,Arial,sans-serif"


def _button(label: str, url_var: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:24px 0;"><tr><td align="center" bgcolor="' + BLUE + '" '
        'style="border-radius:8px;">'
        '<a href="' + url_var + '" target="_blank" style="display:inline-block;'
        "padding:13px 30px;font-family:" + FONT + ";font-size:15px;font-weight:600;"
        'color:#FFFFFF;text-decoration:none;border-radius:8px;">'
        + label
        + "</a></td></tr></table>"
    )


def _fallback_link(url_var: str) -> str:
    return (
        '<p style="margin:0;font-size:12px;line-height:18px;color:' + MUTED + ';">'
        "If the button doesn't work, copy and paste this link into your browser:<br>"
        '<a href="' + url_var + '" style="color:' + BLUE + ';word-break:break-all;">'
        + url_var
        + "</a></p>"
    )


def _p(text: str) -> str:
    return (
        '<p style="margin:0 0 14px;font-size:15px;line-height:24px;color:#334155;">'
        + text
        + "</p>"
    )


def _h1(text: str) -> str:
    return (
        '<h1 style="margin:0 0 16px;font-size:22px;line-height:30px;'
        "font-weight:600;color:" + INK + ';">' + text + "</h1>"
    )


def _note(text: str) -> str:
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="margin:8px 0 18px;"><tr><td style="background:#EFF6FF;'
        "border-left:4px solid " + BLUE + ";border-radius:6px;padding:12px 16px;"
        "font-size:13px;line-height:20px;color:#1E3A8A;font-family:" + FONT + ';">'
        + text
        + "</td></tr></table>"
    )


def _layout(preheader: str, content: str) -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Evolvus 360</title></head>"
        '<body style="margin:0;padding:0;background:' + BG + ';">'
        '<div style="display:none;max-height:0;overflow:hidden;opacity:0;">'
        + preheader
        + "</div>"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" bgcolor="' + BG + '"><tr><td align="center" '
        'style="padding:32px 12px;">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;max-width:560px;background:#FFFFFF;'
        "border:1px solid " + BORDER + ";border-top:4px solid " + BLUE + ";"
        'border-radius:12px;">'
        # header
        '<tr><td style="padding:26px 36px 18px;border-bottom:1px solid ' + BORDER + ';'
        "font-family:" + FONT + ';font-size:24px;font-weight:600;color:' + INK + ';">'
        'evolvus <span style="color:' + GREEN + ';">360</span></td></tr>'
        # body
        '<tr><td style="padding:30px 36px 20px;font-family:' + FONT + ';">'
        + content
        + "</td></tr>"
        # footer
        '<tr><td style="padding:18px 36px 26px;border-top:1px solid ' + BORDER + ";"
        "background:#F8FAFC;border-radius:0 0 12px 12px;font-family:" + FONT + ";"
        "font-size:12px;line-height:18px;color:" + MUTED + ';">'
        "This is an automated message from Evolvus 360. Please do not reply to "
        "this email.<br>&copy; Evolvus 360. All rights reserved."
        "</td></tr></table></td></tr></table></body></html>"
    )


INVITATION_HTML = _layout(
    "Complete your Evolvus 360 profile.",
    _h1("Complete your profile")
    + _p("Hello $employee_name,")
    + _p(
        "Evolvus 360 has invited you to complete your profile. "
        "Click the button below to get started."
    )
    + _button("Complete your profile", "$invitation_link")
    + _note("This link expires in <strong>$expiry_hours hours</strong>.")
    + _fallback_link("$invitation_link"),
)

PASSWORD_RESET_HTML = _layout(
    "Reset your Evolvus 360 password.",
    _h1("Reset your password")
    + _p(
        "We received a request to reset your Evolvus 360 password. "
        "Click the button below to choose a new one."
    )
    + _button("Reset password", "$reset_link")
    + _note(
        "This is a single-use link. If you didn't request a reset, "
        "you can safely ignore this email."
    )
    + _fallback_link("$reset_link"),
)

WELCOME_HTML = _layout(
    "Welcome aboard!",
    _h1("Welcome to $company_name")
    + _p("Hello $employee_name,")
    + _p(
        "We're happy to have you on board at <strong>$company_name</strong>. "
        "Your account is all set, and you can now start using Evolvus 360."
    )
    + _p("If you need any help getting started, reach out to your HR team."),
)

PROFILE_SUBMITTED_HTML = _layout(
    "A new employee profile is waiting for review.",
    _h1("Profile submitted for review")
    + _p("Hello,")
    + _p(
        "<strong>$employee_name</strong> has submitted an employee profile. "
        "Please review it in the Approval Hub."
    )
    + _note("Action required: review and approve or request changes."),
)

PROFILE_APPROVED_HTML = _layout(
    "Your profile has been approved.",
    _h1("Your profile is approved")
    + _p("Hello $employee_name,")
    + _p(
        "Good news! Your profile at <strong>$company_name</strong> has been "
        "reviewed and approved by HR."
    )
    + _p("You can now sign in and access your Evolvus 360 workspace."),
)

GENERAL_HTML = _layout(
    "$subject_line",
    _h1("$subject_line")
    + '<p style="margin:0 0 14px;font-size:15px;line-height:24px;color:#334155;'
    'white-space:pre-line;">$message_text</p>',
)

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
        "body_html": INVITATION_HTML,
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
        "body_text": (
            "Use this single-use link to reset your password: $reset_link\n\n"
            "If you didn't request this, you can ignore this email."
        ),
        "body_html": PASSWORD_RESET_HTML,
        "description": "Single-use password reset email.",
        "required_variables": ["reset_link"],
    },
    {
        "template_key": "WELCOME_EMAIL",
        "name": "Welcome",
        "subject": "Welcome to $company_name, $employee_name",
        "body_text": "Hello $employee_name, welcome to $company_name.",
        "body_html": WELCOME_HTML,
        "description": "Welcome email for newly onboarded employees.",
        "required_variables": ["employee_name", "company_name"],
    },
    {
        "template_key": "EMPLOYEE_PROFILE_SUBMITTED",
        "name": "Employee profile submitted",
        "subject": "Employee profile submitted: $employee_name",
        "body_text": "$employee_name submitted an employee profile for review.",
        "body_html": PROFILE_SUBMITTED_HTML,
        "description": "HR notification when employee onboarding is submitted.",
        "required_variables": ["employee_name"],
    },
    {
        "template_key": "EMPLOYEE_PROFILE_APPROVED",
        "name": "Employee profile approved",
        "subject": "Your Evolvus360 profile is approved",
        "body_text": "Hello $employee_name, your profile at $company_name is approved.",
        "body_html": PROFILE_APPROVED_HTML,
        "description": "Employee notification after HR profile approval.",
        "required_variables": ["employee_name", "company_name"],
    },
    {
        "template_key": "GENERAL_NOTIFICATION",
        "name": "General notification",
        "subject": "$subject_line",
        "body_text": "$message_text",
        "body_html": GENERAL_HTML,
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
                else:
                    # update ALL built-ins so the new design reaches existing DBs
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