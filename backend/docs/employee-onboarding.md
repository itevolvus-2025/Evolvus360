# Employee management and invitation onboarding

This module reuses `users`, `roles`, `user_roles`, and the existing employee,
personal, contact, bank, document, skills, and invitation tables. Departments
are global records. The HRMS has no companies registry table or `company_id`
columns; departments, entities, and employee records are not scoped by company.
There are dropdown APIs but no master-data write APIs in this module.

Apply the schema update from `backend`:

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

## Access

All `/master-data` and `/users` endpoints require a bearer access token and an
active `HR` or `SUPER_ADMIN` role. Department and employee records are available
globally to these roles. Role IDs are loaded from the active roles table; HR may
not assign the Super Admin role.

## Master data

```http
GET /api/v1/master-data/departments
GET /api/v1/master-data/entities
GET /api/v1/master-data/roles
```

The department, entity, and role dropdowns return active records. Responses
contain IDs, names, and codes; role responses use `name` and `code`.

Example response:

```json
{
  "statusCode": 200,
  "message": "Departments fetched successfully",
  "data": [
    {"id": "DEPARTMENT_UUID", "name": "Software Development", "code": "SOFTWARE"}
  ]
}
```

## Create an employee

```http
POST /api/v1/users
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "first_name": "Jhon",
  "middle_name": null,
  "last_name": "Doe",
  "department_id": "DEPARTMENT_UUID",
  "role_id": "ROLE_UUID",
  "designation": "HR Generalist",
  "entity_id": "ENTITY_UUID",
  "location": "Pune",
  "company_email": "jhon.doe@evolvus360.com",
  "personal_email": "jhon.doe@gmail.com",
  "pf_applicable": true,
  "joining_date": "2026-11-24",
  "start_date": "2026-11-24",
  "end_date": null
}
```

The selected department, entity, and role must be active. `employee_code`
is rejected if supplied; the backend locks the entity row and generates the
next two-character uppercase prefix plus three-digit sequence, such as `ET-001`,
from existing employee codes in the same transaction.

```json
{
  "statusCode": 201,
  "message": "Employee created successfully",
  "data": {
    "id": "USER_UUID",
    "employee_code": "ET-001",
    "profile_status": "PENDING"
  }
}
```

Creation does not send an email and leaves the account in `INVITED` state.

## Send and validate invitation

```http
POST /api/v1/users/USER_UUID/invite
Authorization: Bearer <access-token>
```

The invitation link is sent to `personal_email`. Resending rotates the stored
token hash and invalidates the previous link. The response contains status and
expiration only, never the raw token.

```json
{
  "statusCode": 200,
  "message": "Employee invitation sent",
  "data": {"invitation_status": "SENT", "expires_at": "2026-11-20T12:00:00Z"}
}
```

The public validation request is:

```http
POST /api/v1/onboarding/invitations/validate
Content-Type: application/json
```

```json
{"token": "INVITATION_TOKEN_FROM_EMAIL"}
```

Only employee first/last name, entity display name, and expiry are returned.
Invalid, expired, revoked, and already accepted tokens are rejected.

## Submit onboarding

```http
POST /api/v1/onboarding/submit
Content-Type: multipart/form-data
```

Required form fields: `token`, `date_of_birth`, `gender`, `mobile_number`,
`aadhaar_number`, `pan_number`, `emergency_contact_name`,
`emergency_contact_phone`, `emergency_contact_relationship`, `bank_name`,
`account_number`, `ifsc_code`, `new_password`, and `confirm_password`.
Optional fields: `passport_number`, `qualification`, and `languages` (a JSON
array such as `["English","Hindi"]`). Attach both `identity_proof` and
`cancelled_cheque` files. Accepted content is PDF, JPEG, or PNG and each file is
limited by `MAX_ONBOARDING_FILE_SIZE_BYTES` (default 5 MiB).

The invitation token authorizes this public request. On success the service
encrypts sensitive identifiers, saves files under the private upload directory,
marks the invitation accepted and profile submitted, and activates the account
with the employee-provided password in one database transaction.

```json
{
  "statusCode": 200,
  "message": "Employee profile submitted successfully",
  "data": {"profile_status": "SUBMITTED"}
}
```

## List, view, edit, and approve

```http
GET /api/v1/users?search=jhon&role_id=ROLE_UUID&department_id=DEPARTMENT_UUID&entity_id=ENTITY_UUID&profile_status=PENDING&account_status=ACTIVE&page=1&page_size=10
GET /api/v1/users/USER_UUID
PUT /api/v1/users/USER_UUID
POST /api/v1/users/USER_UUID/approve
```

All require HR/Super Admin authorization. List responses omit
personal, contact, bank, and document details. Details return only HR-entered
fields while pending (`employee_details: null`); submitted/approved profiles
include employee details, with government identifiers and bank account numbers
masked and documents represented by metadata. Updates accept only HR-managed
fields and cannot change employee codes or overwrite employee-submitted fields.
Approval is allowed only from `SUBMITTED` and requires both onboarding documents
and personal, contact, and bank records.

List response:

```json
{
  "statusCode": 200,
  "message": "Users fetched successfully",
  "data": {
    "items": [
      {
        "id": "USER_UUID",
        "first_name": "Jhon",
        "middle_name": null,
        "last_name": "Doe",
        "employee_code": "ET-001",
        "department": {"id": "DEPARTMENT_UUID", "name": "Software Development"},
        "role": {"id": "ROLE_UUID", "name": "HR"},
        "designation": "HR Generalist",
        "entity": {"id": "ENTITY_UUID", "name": "ETPL", "code": "ETPL"},
        "location": "Pune",
        "account_status": "INVITED",
        "profile_status": "PENDING"
      }
    ],
    "pagination": {"page": 1, "page_size": 10, "total": 1, "total_pages": 1}
  }
}
```

Pending detail response includes `can_view_employee_details: false` and
`employee_details: null`; the `hr_details` object contains the fields above and
the HR-entered email and employment dates.

Update body fields are optional; use any subset of:

```json
{
  "first_name": "Jhon",
  "department_id": "DEPARTMENT_UUID",
  "role_id": "ROLE_UUID",
  "designation": "HR Generalist",
  "entity_id": "ENTITY_UUID",
  "location": "Pune",
  "company_email": "jhon.doe@evolvus360.com",
  "personal_email": "jhon.doe@gmail.com",
  "pf_applicable": true,
  "joining_date": "2026-11-24",
  "start_date": "2026-11-24",
  "end_date": null
}
```

Approval response:

```json
{
  "statusCode": 200,
  "message": "Employee profile approved successfully",
  "data": {"profile_status": "APPROVED"}
}
```

## Required settings and deployment notes

- `PII_ENCRYPTION_KEY`: Fernet key. Generate with
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Keep the same managed secret available to all application instances and back
  it up; losing it makes encrypted identifiers unreadable.
- `PRIVATE_UPLOAD_DIR`: private filesystem location; default is
  `private_uploads` relative to the backend working directory. Do not expose it
  through a static web server.
- `MAX_ONBOARDING_FILE_SIZE_BYTES`: per-file limit, default 5 MiB and maximum
  5 MiB due to the existing document table constraint.
- `ONBOARDING_INVITATION_EXPIRE_HOURS`: invitation lifetime, default 48.
- `FRONTEND_ONBOARDING_URL`: frontend onboarding page base URL.
- Existing `EMAIL_BACKEND`, SMTP, `DATABASE_URL`, and JWT settings also apply.

The console email backend deliberately logs no invitation URL or raw token, so it
cannot deliver a clickable invitation. Use a development SMTP catcher or another
SMTP test account to exercise the complete invitation flow. Local filesystem
storage is implemented for private uploads; production deployments should point
it to protected persistent storage or replace the storage adapter with a private
object-storage service. Configure `PII_ENCRYPTION_KEY` before accepting any
onboarding submissions.

## Local verification and end-to-end sequence

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
.\.venv\Scripts\python.exe -m pytest app/tests -p no:cacheprovider -q
.\.venv\Scripts\ruff.exe check app
.\.venv\Scripts\ruff.exe format --check app
```

For a complete application flow, configure a valid development `PII_ENCRYPTION_KEY`
and a development SMTP catcher, seed active department/entity rows and the HR,
Super Admin, and employee roles, then:

1. Log in as HR or Super Admin and fetch the three master-data dropdowns.
2. Create an employee with active department/entity/role IDs.
3. Send the invitation and open the emailed frontend URL.
4. Validate the invitation token, then submit the multipart onboarding form with
   both required documents and an initial password.
5. Confirm the employee can log in, the management list shows `SUBMITTED`, and
   the detail response masks sensitive identifiers.
6. Approve the submitted profile and confirm status `APPROVED` and audit fields.

Automated tests cover metadata, route registration, migration SQL generation,
employee-code prefix validation, schema restrictions, and existing auth/session
behavior. A live SMTP, private-storage, encrypted PII, and multi-user concurrent
database integration run is still required in the target deployment environment.
