"""Import all ORM models so Base.metadata is complete for Alembic."""

from app.models.company import Company
from app.models.hrms import (
    Department,
    EmailDispatchOutbox,
    EmployeeBankDetails,
    EmployeeContactDetails,
    EmployeeDocuments,
    EmployeeEmploymentDetails,
    EmployeePersonalDetails,
    EmployeeSkillsAndInterests,
    Entity,
    OnboardingInvitation,
    PasswordResetToken,
    Permission,
    RefreshTokenSession,
    Role,
    RolePermission,
    User,
    UserRole,
)

__all__ = [
    "EmailDispatchOutbox",
    "Company",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "RefreshTokenSession",
    "EmployeeEmploymentDetails",
    "EmployeePersonalDetails",
    "EmployeeContactDetails",
    "EmployeeBankDetails",
    "EmployeeDocuments",
    "EmployeeSkillsAndInterests",
    "Department",
    "Entity",
    "OnboardingInvitation",
    "PasswordResetToken",
]
