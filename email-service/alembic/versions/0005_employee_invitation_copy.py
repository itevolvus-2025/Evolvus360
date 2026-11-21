"""Update the employee invitation email copy.

Revision ID: 0005_employee_invitation_copy
Revises: 0004_uuid_pk_defaults
"""

from typing import Sequence

from alembic import op


revision: str = "0005_employee_invitation_copy"
down_revision: str | Sequence[str] | None = "0004_uuid_pk_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE email_templates
        SET subject = 'Evolvus360 invited you to complete your profile',
            body_text = 'Hello $employee_name,\n\nEvolvus360 has invited you to complete your profile. Please follow the link below to complete your profile:\n$invitation_link\n\nThis link expires in $expiry_hours hours.',
            body_html = '<p>Hello $employee_name,</p><p>Evolvus360 has invited you to complete your profile. Please follow the link below to complete your profile:</p><p><a href="$invitation_link">Complete your profile</a></p><p>This link expires in $expiry_hours hours.</p>',
            required_variables = '["employee_name", "invitation_link", "expiry_hours"]'::jsonb
        WHERE template_key = 'EMPLOYEE_INVITATION'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE email_templates
        SET subject = 'Complete your Evolvus360 onboarding, $employee_name',
            body_text = 'Hello $employee_name,\n\n$company_name invited you to complete your employee onboarding. Open this secure link: $invitation_link\n\nThis link expires in $expiry_hours hours.',
            body_html = '<p>Hello $employee_name,</p><p>$company_name invited you to complete your employee onboarding.</p><p><a href="$invitation_link">Complete onboarding</a></p><p>This link expires in $expiry_hours hours.</p>',
            required_variables = '["employee_name", "company_name", "invitation_link", "expiry_hours"]'::jsonb
        WHERE template_key = 'EMPLOYEE_INVITATION'
        """
    )
