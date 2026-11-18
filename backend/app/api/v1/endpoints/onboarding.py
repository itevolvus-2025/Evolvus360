"""Public, single-use invitation-authorized employee onboarding routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.schemas.auth import ApiResponse
from app.schemas.employee import InvitationTokenRequest
from app.services import employee_service
from app.utils.responses import success_response

router = APIRouter(prefix="/onboarding", tags=["Employee onboarding"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/invitations/validate", response_model=ApiResponse[dict])
def validate_invitation(payload: InvitationTokenRequest, db: DbSession):
    return success_response(
        "Invitation is valid", employee_service.validate_invitation(db, payload.token)
    )


@router.post("/submit", response_model=ApiResponse[dict])
async def submit_onboarding(
    db: DbSession,
    token: Annotated[str, Form(min_length=32, max_length=256)],
    date_of_birth: Annotated[date, Form()],
    gender: Annotated[str, Form(min_length=1, max_length=20)],
    mobile_number: Annotated[str, Form(min_length=5, max_length=25)],
    aadhaar_number: Annotated[str, Form(min_length=12, max_length=20)],
    pan_number: Annotated[str, Form(min_length=10, max_length=10)],
    emergency_contact_name: Annotated[str, Form(min_length=1, max_length=150)],
    emergency_contact_phone: Annotated[str, Form(min_length=5, max_length=25)],
    emergency_contact_relationship: Annotated[str, Form(min_length=1, max_length=50)],
    bank_name: Annotated[str, Form(min_length=1, max_length=150)],
    account_number: Annotated[str, Form(min_length=4, max_length=50)],
    ifsc_code: Annotated[str, Form(min_length=11, max_length=11)],
    new_password: Annotated[str, Form(min_length=12, max_length=128)],
    confirm_password: Annotated[str, Form(min_length=12, max_length=128)],
    identity_proof: Annotated[UploadFile, File()],
    cancelled_cheque: Annotated[UploadFile, File()],
    passport_number: Annotated[str | None, Form(max_length=30)] = None,
    qualification: Annotated[str | None, Form(max_length=4000)] = None,
    languages: Annotated[str, Form()] = "[]",
):
    settings = get_settings()
    limit = settings.max_onboarding_file_size_bytes + 1
    identity_bytes = await identity_proof.read(limit)
    cheque_bytes = await cancelled_cheque.read(limit)
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
            "qualification": qualification,
            "languages": languages,
            "new_password": new_password,
            "confirm_password": confirm_password,
        },
        {
            "identity_proof": (
                identity_proof.filename or "identity_proof",
                identity_proof.content_type,
                identity_bytes,
            ),
            "cancelled_cheque": (
                cancelled_cheque.filename or "cancelled_cheque",
                cancelled_cheque.content_type,
                cheque_bytes,
            ),
        },
    )
    return success_response("Employee profile submitted successfully", result)
