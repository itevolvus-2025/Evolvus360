"""Shared strict validation helpers for employee data."""

import re


FIRST_NAME_ERROR = (
    "First name must contain only letters and spaces."
)
MIDDLE_NAME_ERROR = (
    "Middle name must contain only letters and spaces."
)
LAST_NAME_ERROR = (
    "Last name must contain only letters and spaces."
)
DESIGNATION_ERROR = (
    "Designation must contain only letters and spaces."
)
LOCATION_ERROR = (
    "Location must contain only letters and spaces."
)
MOBILE_ERROR = (
    "Mobile number must be exactly 10 digits and start with a digit between 6 and 9."
)
AADHAAR_LENGTH_ERROR = "Aadhaar number must contain exactly 12 digits."
AADHAAR_CHECKSUM_ERROR = (
    "Invalid Aadhaar number. Please check the entered number."
)
PAN_ERROR = (
    "Invalid PAN. Expected format: 5 letters, 4 digits and 1 letter (AAAAA9999A)."
)

_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def has_valid_verhoeff(value: str) -> bool:
    checksum = 0
    for index, character in enumerate(reversed(value)):
        checksum = _VERHOEFF_D[
            checksum
        ][_VERHOEFF_P[index % 8][int(character)]]
    return checksum == 0


def validate_name(value: str, error: str, *, required: bool = True) -> str:
    value = " ".join(value.split())
    if not value and not required:
        return value
    if not value or any(not (character.isalpha() or character == " ") for character in value):
        raise ValueError(error)
    return value


def validate_mobile(value: str) -> str:
    if not re.fullmatch(r"[6-9][0-9]{9}", value):
        raise ValueError(MOBILE_ERROR)
    return value


def validate_aadhaar(value: str) -> str:
    if not re.fullmatch(r"[0-9]{12}", value):
        raise ValueError(AADHAAR_LENGTH_ERROR)
    if not has_valid_verhoeff(value):
        raise ValueError(AADHAAR_CHECKSUM_ERROR)
    return value


def validate_pan(value: str) -> str:
    value = value.upper()
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", value):
        raise ValueError(PAN_ERROR)
    return value
