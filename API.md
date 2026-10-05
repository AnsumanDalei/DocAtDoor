# DocAtDoor REST API

Base path: `/api/`. JSON responses. Doctor-directory results are paginated (20 per page). Token clients send `Authorization: Token <token>`. Same-origin Django sessions are also accepted; unsafe session-authenticated requests require CSRF.

## Authentication and profiles

| Method and path | Access | Behavior |
|---|---|---|
| `POST /auth/register/` | Public, throttled | Patient-only account creation and email verification code delivery. Accepts name, email, password, optional phone, age (1–120), gender (female/male/non-binary/prefer not to say), blood group (A/B/AB/O positive or negative), and optional JPG/PNG/WebP image profile picture (5 MB max). Submitted roles and doctor-only fields are ignored. Send JSON for text-only registration or multipart form data when uploading a picture. |
| `POST /auth/token/` | Public, throttled | Email/password login. Returns a token only for active, email-verified users. If the same email and password match two accounts, responds with `409` and the account choices; repeat with the selected `account_id` and the same credentials. |
| `POST /auth/logout/` | Authenticated | Revokes the caller's token. |
| `GET /auth/verification-status/` | Authenticated | Reads the caller's email verification state. |
| `POST /auth/verify-email/`, `/auth/resend-verification/` | Public, throttled | Existing email OTP verification and resend flows. |
| `POST /auth/password-reset/`, `/auth/password-reset/confirm/` | Public, throttled | Request a reset link or set a new password using its token. |
| `POST /auth/change-password/` | Authenticated | Changes password and revokes existing API token. |
| `GET/PATCH /profile/` | Patient or doctor | Reads/updates the caller's own permitted fields; role and verification remain read-only. |

## Doctor directory and availability

| Method and path | Access | Behavior |
|---|---|---|
| `GET /doctors/` | Public | Verified doctor list; supports `q`, `area`, `specialization`, `min_experience`, `max_fee`, and `available` filters. |
| `GET /doctors/{id}/` | Public | Verified doctor public profile. |
| `GET /doctors/{id}/availability/?date=YYYY-MM-DD` | Public | Real open visit start times, subject to the booking window and doctor's configured availability. |
| `GET/POST /availability/` | Doctor | Read or add the authenticated doctor's weekly slots. |
| `DELETE /availability/{id}/` | Owning doctor | Delete own slot unless an upcoming pending/confirmed appointment depends on it. |

## Appointments and care

| Method and path | Access | Behavior |
|---|---|---|
| `GET/POST /appointments/` | Patient | List own visits or request one; validates doctor, slot, and conflicts. |
| `GET /appointments/doctor/` | Doctor | Assigned visits plus upcoming unassigned requests. |
| `GET /appointments/{id}/` | Patient owner / assigned doctor / eligible doctor viewing open request | Read authorized visit only. |
| `POST /appointments/{id}/accept/`, `/reject/`, `/complete/` | Doctor | Enforce visit state, assignment, and verified/available status where accepting. |
| `POST /appointments/{id}/cancel/`, `/reschedule/` | Patient owner | Change own upcoming pending or accepted visit; reschedule revalidates availability. |
| `GET/POST /appointments/{id}/consultation/` | Assigned doctor writes; patient owner reads | Consultation details are not returned by appointment list/detail. |
| `POST /appointments/{id}/prescription/` | Assigned doctor | Upload a validated prescription for a completed visit. |
| `GET /records/reports/`, `POST /records/reports/` | Patient | List or upload own validated medical reports. |
| `DELETE /records/reports/{id}/` | Patient owner | Delete own report. |
| `GET /records/reports/{id}/download/` | Patient owner | Authenticated protected download. |
| `GET /records/prescriptions/` | Patient owner / prescribing doctor | List authorized prescription metadata. |
| `GET /records/prescriptions/{id}/download/` | Patient owner / prescribing doctor | Authenticated protected download. |
| `POST /reviews/appointments/{id}/` | Patient owner | Review own completed doctor visit. |
| `GET /doctors/{id}/reviews/` | Public | Public review list for verified doctor. |
| `GET /notifications/`, `PATCH /notifications/{id}/`, `POST /notifications/read-all/` | Authenticated recipient | List and update only own notifications. `DELETE /notifications/{id}/` is also supported. |
| `POST /service-enquiries/` | Public, throttled | Add enquiry to staff queue; honeypot field is `website`. |

## Limits and operational notes

There are no public admin-management endpoints. Registration cannot create doctors; administrators create/verify doctor accounts through the existing admin workflow. Phone OTP/SMS has no provider and is not implemented. Flutter clients use the token route, the same Django API and the same MySQL database as the website.

Medical reports and prescriptions are validated by extension, size, and file signature, and are returned only by ownership-checked download views. Do not serve `protected_media/` as a public static directory. Email delivery requires configured SMTP; local default email backend suppresses messages and does not log OTPs or reset links.

MySQL is the configured application database. A local MySQL80 service is present but app credentials are unavailable (connection error 1045); its installed version is 8.0.46, not the required 8.4. Django/API tests use explicit temporary SQLite overrides and therefore do not verify MySQL compatibility. The GitHub Actions workflow is configured to test with MySQL but has not run in GitHub. See `DEPLOYMENT.md` for deployment limitations.
