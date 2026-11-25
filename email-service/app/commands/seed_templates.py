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
    "Action required: complete your Evolvus 360 profile.",
    _h1("Complete your profile")
    + _p("Dear $employee_name,")
    + _p(
        "Welcome to Evolvus 360. Your account has been created, and you have "
        "been invited to complete your employee profile."
    )
    + _p(
        "Please use the secure button below to submit your personal and "
        "professional details."
    )
    + _button("Complete your profile", "$invitation_link")
    + _note(
        "For security reasons, this link will expire in "
        "<strong>$expiry_hours hours</strong>. If it expires, please contact "
        "your HR team to request a new invitation."
    )
    + _fallback_link("$invitation_link")
    + '<p style="margin:18px 0 0;font-size:13px;line-height:20px;color:' + MUTED + ';">'
    "If you were not expecting this email, please notify your HR administrator.</p>",
)

PASSWORD_RESET_HTML = _layout(
    "Reset your Evolvus 360 password.",
    _h1("Reset your password")
    + _p("Hello,")
    + _p(
        "We received a request to reset the password for your Evolvus 360 "
        "account. Please use the secure button below to set a new password."
    )
    + _button("Reset password", "$reset_link")
    + _note(
        "This link can be used only once. If you did not request a password "
        "reset, no action is needed and your password will remain unchanged. "
        "If you are concerned about your account security, please contact your "
        "system administrator."
    )
    + _fallback_link("$reset_link"),
)

WELCOME_HTML = _layout(
    "Welcome to $company_name.",
    _h1("Welcome to $company_name")
    + _p("Dear $employee_name,")
    + _p(
        "Welcome to <strong>$company_name</strong>. We are pleased to have you "
        "on board."
    )
    + _p(
        "Your Evolvus 360 account is now active, and you can sign in to access "
        "your workspace. If you need any assistance getting started, please "
        "reach out to your HR team."
    )
    + _p("We wish you a great start and a successful journey with us."),
)

PROFILE_SUBMITTED_HTML = _layout(
    "A new employee profile is waiting for your review.",
    _h1("Profile submitted for review")
    + _p("Hello,")
    + _p(
        "<strong>$employee_name</strong> has completed and submitted their "
        "employee profile."
    )
    + _p(
        "Please review the submitted details in the Approval Hub and approve "
        "the profile or request changes at your earliest convenience."
    )
    + _note("Action required: review and approve, or request changes."),
)


PROFILE_APPROVED_HTML = _layout(
    "Your Evolvus 360 employee account has been approved.",
    _h1("Your Employee Account Has Been Approved")
    + _p("Hello $employee_name,")
    + _p(
        "We are pleased to inform you that your onboarding request "
        "has been successfully approved by the HR team."
    )
    + _p(
        "Your employee account at <strong>$company_name</strong> "
        "is now active. You can use the login credentials below "
        "to access your Evolvus 360 workspace."
    )
    # Login Credentials
    + '<table role="presentation" width="100%" cellpadding="0" '
    'cellspacing="0" border="0" '
    'style="margin:20px 0;background:#F8FAFC;'
    'border:1px solid ' + BORDER + ';border-radius:8px;">'
    '<tr><td style="padding:18px 20px;'
    'font-family:' + FONT + ';font-size:14px;'
    'line-height:24px;color:#334155;">'
    '<strong style="color:' + INK + ';">Login ID</strong><br>'
    '<a href="mailto:$employee_email" '
    'style="color:' + BLUE + ';text-decoration:none;">'
    '$employee_email</a><br><br>'
    '<strong style="color:' + INK + ';">Temporary Password</strong><br>'
    '<span style="color:' + INK + ';">$temporary_password</span>'
    '</td></tr></table>'
    # Login Button
    + _button("Login to Evolvus 360", "$login_url")
    # Important Notice
    + _note(
        "<strong>Important:</strong> Please sign in within "
        "<strong>24 hours</strong> using your temporary password. "
        "You must change your password immediately after your first login."
    )
    # Fallback Login URL
    + _fallback_link("$login_url")
    + _p(
        "If you experience any issues accessing your account, "
        "please contact your HR administrator."
    )
    + _p(
        "Welcome to Evolvus 360!<br><br>"
        "Best Regards,<br>"
        "<strong>Evolvus 360 Team</strong>"
    ),
)


GENERAL_HTML = _layout(
    "$subject_line",
    _h1("$subject_line")
    + _p("Hello,")
    + '<p style="margin:0 0 14px;font-size:15px;line-height:24px;color:#334155;'
    'white-space:pre-line;">$message_text</p>',
)

DEFAULT_TEMPLATES = (
    {
        "template_key": "EMPLOYEE_INVITATION",
        "name": "Employee invitation",
        "subject": "Action required: Complete your Evolvus 360 profile",
        "body_text": (
            "Dear $employee_name,\n\n"
            "Welcome to Evolvus 360. Your account has been created, and you "
            "have been invited to complete your employee profile.\n\n"
            "Please use the secure link below to submit your personal and "
            "professional details:\n\n$invitation_link\n\n"
            "For security reasons, this link will expire in $expiry_hours "
            "hours. If it expires, please contact your HR team to request a "
            "new invitation.\n\n"
            "If you were not expecting this email, please notify your HR "
            "administrator.\n\n"
            "Regards,\nEvolvus 360 Team"
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
        "subject": "Reset your Evolvus 360 password",
        "body_text": (
            "Hello,\n\n"
            "We received a request to reset the password for your Evolvus 360 "
            "account.\n\n"
            "Please use the secure link below to set a new password:\n\n"
            "$reset_link\n\n"
            "This link can be used only once. If you did not request a "
            "password reset, no action is needed and your password will remain "
            "unchanged. If you are concerned about your account security, "
            "please contact your system administrator.\n\n"
            "Regards,\nEvolvus 360 Team"
        ),
        "body_html": PASSWORD_RESET_HTML,
        "description": "Single-use password reset email.",
        "required_variables": ["reset_link"],
    },
    {
        "template_key": "WELCOME_EMAIL",
        "name": "Welcome",
        "subject": "Welcome to $company_name, $employee_name",
        "body_text": (
            "Dear $employee_name,\n\n"
            "Welcome to $company_name. We are pleased to have you on board.\n\n"
            "Your Evolvus 360 account is now active, and you can sign in to "
            "access your workspace. If you need any assistance getting "
            "started, please reach out to your HR team.\n\n"
            "We wish you a great start and a successful journey with us.\n\n"
            "Regards,\n$company_name Team"
        ),
        "body_html": WELCOME_HTML,
        "description": "Welcome email for newly onboarded employees.",
        "required_variables": ["employee_name", "company_name"],
    },
    {
        "template_key": "EMPLOYEE_PROFILE_SUBMITTED",
        "name": "Employee profile submitted",
        "subject": "Profile submitted for review: $employee_name",
        "body_text": (
            "Hello,\n\n"
            "$employee_name has completed and submitted their employee "
            "profile.\n\n"
            "Please review the submitted details in the Approval Hub and "
            "approve the profile or request changes at your earliest "
            "convenience.\n\n"
            "Regards,\nEvolvus 360 Team"
        ),
        "body_html": PROFILE_SUBMITTED_HTML,
        "description": "HR notification when employee onboarding is submitted.",
        "required_variables": ["employee_name"],
    },
   
{
    "template_key": "EMPLOYEE_PROFILE_APPROVED",
    "name": "Employee profile approved",
    "subject": "Your Evolvus 360 Employee Account Has Been Approved",
    "body_text": (
        "Hello $employee_name,\n\n"
        "We are pleased to inform you that your onboarding request "
        "has been successfully approved by the HR team.\n\n"
        "Your employee account at $company_name is now active.\n\n"
        "Login Details:\n"
        "Login ID: $employee_email\n"
        "Temporary Password: $temporary_password\n"
        "Login URL: $login_url\n\n"
        "Please sign in within 24 hours using your temporary "
        "password and change your password immediately after "
        "your first login.\n\n"
        "Welcome to Evolvus 360!\n\n"
        "Best Regards,\n"
        "Evolvus 360 Team"
    ),
    "body_html": PROFILE_APPROVED_HTML,
    "description": "Employee account approval notification with login credentials.",
    "required_variables": [
        "employee_name",
        "company_name",
        "employee_email",
        "temporary_password",
        "login_url",
    ],
},

    {
        "template_key": "GENERAL_NOTIFICATION",
        "name": "General notification",
        "subject": "$subject_line",
        "body_text": "Hello,\n\n$message_text\n\nRegards,\nEvolvus 360 Team",
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