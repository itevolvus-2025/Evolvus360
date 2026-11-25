"""Public, single-use invitation-authorized employee onboarding routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import ApiResponse
from app.schemas.employee import InvitationTokenRequest
from app.schemas.validators import (
    validate_aadhaar,
    validate_mobile,
    validate_pan,
)
from app.services import employee_service
from app.utils.responses import success_response

router = APIRouter(prefix="/onboarding", tags=["Employee onboarding"])
employee_router = APIRouter(prefix="/employee/onboarding", tags=["Employee onboarding"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
MobileForm = Annotated[str, Form(), AfterValidator(validate_mobile)]
EmergencyMobileForm = Annotated[str, Form(), AfterValidator(validate_mobile)]
AadhaarForm = Annotated[str, Form(), AfterValidator(validate_aadhaar)]
PanForm = Annotated[str, Form(), AfterValidator(validate_pan)]


@employee_router.get("/form", response_model=ApiResponse[dict])
def get_onboarding_form(db: DbSession, user: CurrentUser):
    return success_response(
        "Onboarding form fetched successfully",
        employee_service.get_employee_onboarding_form(db, user),
    )


@employee_router.post("/submit", response_model=ApiResponse[dict])
async def submit_employee_form(
    db: DbSession,
    user: CurrentUser,
    date_of_birth: Annotated[str, Form()],
    gender: Annotated[str, Form(min_length=1, max_length=20)],
    mobile_number: MobileForm,
    aadhaar_number: AadhaarForm,
    pan_number: PanForm,
    emergency_contact_name: Annotated[str, Form(min_length=1, max_length=150)],
    emergency_contact_phone: EmergencyMobileForm,
    emergency_contact_relationship: Annotated[str, Form(min_length=1, max_length=50)],
    bank_name: Annotated[str, Form(min_length=1, max_length=150)],
    account_number: Annotated[str, Form(min_length=4, max_length=50)],
    ifsc_code: Annotated[str, Form(min_length=11, max_length=11)],
    identity_proof: Annotated[UploadFile, File()],
    cancelled_cheque: Annotated[UploadFile, File()],
    uan_number: Annotated[str | None, Form(max_length=12)] = None,
    passport_number: Annotated[str | None, Form(max_length=30)] = None,
    qualification: Annotated[str | None, Form(max_length=4000)] = None,
    skills: Annotated[str | None, Form(max_length=4000)] = None,
    languages: Annotated[str | None, Form(max_length=1000)] = None,
):
    limit = get_settings().max_onboarding_file_size_bytes + 1
    files = {}
    for kind, upload in (
        ("identity_proof", identity_proof),
        ("cancelled_cheque", cancelled_cheque),
    ):
        files[kind] = (
            upload.filename or kind,
            upload.content_type,
            await upload.read(limit),
        )
    try:
        parsed_date_of_birth = date.fromisoformat(date_of_birth)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Enter a valid date in YYYY-MM-DD format",
        ) from None
    result = employee_service.submit_employee_onboarding(
        db,
        user,
        {
            "date_of_birth": parsed_date_of_birth,
            "gender": gender,
            "mobile_number": mobile_number,
            "aadhaar_number": aadhaar_number,
            "pan_number": pan_number,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_phone": emergency_contact_phone,
            "emergency_contact_relationship": emergency_contact_relationship,
            "bank_name": bank_name,
            "account_number": account_number,
            "ifsc_code": ifsc_code,
            "uan_number": uan_number,
            "passport_number": passport_number,
            "qualification": qualification,
            "skills": skills,
            "languages": languages,
        },
        files,
    )
    return success_response("Employee onboarding submitted successfully", result)


@router.post("/invitations/validate", response_model=ApiResponse[dict])
def validate_invitation(payload: InvitationTokenRequest, db: DbSession):
    return success_response(
        "Invitation is valid", employee_service.get_onboarding_invitation(db, payload.token)
    )


@router.post("/draft", response_model=ApiResponse[dict])
async def save_onboarding_draft(
    db: DbSession,
    token: Annotated[str, Form(min_length=32, max_length=256)],
    date_of_birth: Annotated[str | None, Form()] = None,
    gender: Annotated[str | None, Form(max_length=20)] = None,
    mobile_number: Annotated[str | None, Form(max_length=25)] = None,
    aadhaar_number: Annotated[str | None, Form(max_length=12)] = None,
    pan_number: Annotated[str | None, Form(max_length=10)] = None,
    passport_number: Annotated[str | None, Form(max_length=30)] = None,
    emergency_contact_name: Annotated[str | None, Form(max_length=150)] = None,
    emergency_contact_phone: Annotated[str | None, Form(max_length=25)] = None,
    emergency_contact_relationship: Annotated[str | None, Form(max_length=50)] = None,
    bank_name: Annotated[str | None, Form(max_length=150)] = None,
    account_number: Annotated[str | None, Form(max_length=35)] = None,
    ifsc_code: Annotated[str | None, Form(max_length=11)] = None,
    uan_number: Annotated[str | None, Form(max_length=12)] = None,
    qualification: Annotated[str | None, Form(max_length=4000)] = None,
    languages: Annotated[str | None, Form()] = None,
    identity_proof: UploadFile | None = File(default=None),
    cancelled_cheque: UploadFile | None = File(default=None),
):
    limit = get_settings().max_onboarding_file_size_bytes + 1
    files = {}
    for kind, upload in (
        ("identity_proof", identity_proof),
        ("cancelled_cheque", cancelled_cheque),
    ):
        if upload is not None and upload.filename and upload.size:
            files[kind] = (
                upload.filename,
                upload.content_type,
                await upload.read(limit),
            )
    result = employee_service.save_onboarding_draft(
        db,
        token,
        {
            "date_of_birth": date_of_birth,
            "gender": gender,
            "mobile_number": mobile_number,
            "aadhaar_number": aadhaar_number,
            "pan_number": pan_number,
            "passport_number": passport_number,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_phone": emergency_contact_phone,
            "emergency_contact_relationship": emergency_contact_relationship,
            "bank_name": bank_name,
            "account_number": account_number,
            "ifsc_code": ifsc_code,
            "uan_number": uan_number,
            "qualification": qualification,
            "languages": languages,
        },
        files,
    )
    return success_response(
        "Onboarding draft saved successfully",
        {
            **result,
            "documents": employee_service.documents_for_invitation(db, token),
        },
    )


@router.post("/submit", response_model=ApiResponse[dict])
async def submit_onboarding(
    db: DbSession,
    token: Annotated[str, Form(min_length=32, max_length=256)],
    date_of_birth: Annotated[str | None, Form()] = None,
    gender: Annotated[str | None, Form(max_length=20)] = None,
    mobile_number: Annotated[str | None, Form(max_length=25)] = None,
    aadhaar_number: Annotated[str | None, Form(max_length=12)] = None,
    pan_number: Annotated[str | None, Form(max_length=10)] = None,
    emergency_contact_name: Annotated[str | None, Form(max_length=150)] = None,
    emergency_contact_phone: Annotated[str | None, Form(max_length=25)] = None,
    emergency_contact_relationship: Annotated[str | None, Form(max_length=50)] = None,
    bank_name: Annotated[str | None, Form(max_length=150)] = None,
    account_number: Annotated[str | None, Form(max_length=50)] = None,
    ifsc_code: Annotated[str | None, Form(max_length=11)] = None,
    identity_proof: UploadFile | None = File(default=None),
    cancelled_cheque: UploadFile | None = File(default=None),
    uan_number: Annotated[str | None, Form(max_length=12)] = None,
    passport_number: Annotated[str | None, Form(max_length=30)] = None,
    qualification: Annotated[str | None, Form(max_length=4000)] = None,
    languages: Annotated[str, Form()] = "[]",
):
    settings = get_settings()
    limit = settings.max_onboarding_file_size_bytes + 1
    files = {}
    for kind, upload in (
        ("identity_proof", identity_proof),
        ("cancelled_cheque", cancelled_cheque),
    ):
        if upload is not None and upload.filename:
            files[kind] = (
                upload.filename,
                upload.content_type,
                await upload.read(limit),
            )
    result = employee_service.submit_onboarding(
        db,
        token,
        {
            "date_of_birth": date_of_birth,
            "gender": gender,
            "mobile_number": mobile_number,
            "aadhaar_number": aadhaar_number,
            "pan_number": pan_number,
            "passport_number": passport_number,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_phone": emergency_contact_phone,
            "emergency_contact_relationship": emergency_contact_relationship,
            "bank_name": bank_name,
            "account_number": account_number,
            "ifsc_code": ifsc_code,
            "uan_number": uan_number,
            "qualification": qualification,
            "languages": languages,
        },
        files,
    )
    return success_response("Employee profile submitted successfully", result)
