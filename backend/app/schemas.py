from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================================================
# AUTH
# =========================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "security_officer"


class UserSelfUpdate(BaseModel):
    name: str | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6)


# =========================================================
# STUDENTS
# =========================================================

class StudentCreate(BaseModel):
    student_id: str
    name: str
    department: str
    course: str | None = None
    year: int
    email: EmailStr | None = None
    phone: str | None = None
    biometric_consent: bool = False


class StudentUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    course: str | None = None
    year: int | None = None
    email: EmailStr | None = None
    phone: str | None = None
    biometric_consent: bool | None = None
    status: str | None = None
    profile_image: str | None = None
    face_embedding: str | None = None


class StudentResponse(BaseModel):
    id: int
    student_id: str
    name: str
    department: str
    course: str | None
    year: int
    email: str | None
    phone: str | None
    profile_image: str | None
    status: str
    biometric_consent: bool
    face_enrolled: bool = False
    has_portal_login: bool = False
    vehicles: list["VehicleResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, student):
        data = cls.model_validate(student).model_dump()
        data["face_enrolled"] = bool(student.face_embedding)
        data["has_portal_login"] = bool(student.password_hash)
        data["vehicles"] = [VehicleResponse.model_validate(v) for v in student.vehicles]
        return cls(**data)


# =========================================================
# STUDENT PORTAL (public self-registration + student login)
# =========================================================

class StudentPortalLoginRequest(BaseModel):
    student_id: str
    password: str


class StudentPortalLoginResponse(BaseModel):
    student: StudentResponse
    access_token: str
    token_type: str = "bearer"


class StudentRejectRequest(BaseModel):
    reason: str | None = None


# =========================================================
# VEHICLES
# =========================================================

class VehicleCreate(BaseModel):
    registration_number: str
    vehicle_type: str
    owner_student_id: int
    make: str | None = None
    model: str | None = None
    color: str | None = None


class VehicleUpdate(BaseModel):
    vehicle_type: str | None = None
    make: str | None = None
    model: str | None = None
    color: str | None = None
    status: str | None = None
    is_blocklisted: bool | None = None
    block_reason: str | None = None
    vehicle_image: str | None = None


class VehicleResponse(BaseModel):
    id: int
    registration_number: str
    vehicle_type: str
    make: str | None
    model: str | None
    color: str | None
    vehicle_image: str | None
    owner_student_id: int
    status: str
    is_blocklisted: bool
    block_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# VERIFICATION / ENTRY LOGS
# =========================================================

class VerificationResult(BaseModel):
    entry_id: int
    vehicle_detected: bool
    vehicle_type: str | None
    plate_detected: bool
    plate_number: str | None
    ocr_confidence: float
    vehicle_registered: bool
    student_id: int | None
    student_name: str | None
    face_detected: bool
    face_match: bool | None
    face_similarity: float
    verification_status: str
    status: str
    rejection_reason: str | None
    captured_image: str | None


class EntryResponse(BaseModel):
    id: int
    detected_plate: str | None
    detected_vehicle_type: str | None
    vehicle_id: int | None
    student_id: int | None
    gate_id: int
    captured_image: str | None
    entry_time: datetime
    plate_confidence: float
    face_confidence: float
    plate_match: bool
    face_match: str
    status: str
    verification_status: str
    rejection_reason: str | None
    decision_source: str
    operator_id: int | None

    model_config = ConfigDict(from_attributes=True)


class ManualDecisionRequest(BaseModel):
    status: str  # granted | denied
    reason: str


# =========================================================
# ALERTS
# =========================================================

class AlertResponse(BaseModel):
    id: int
    entry_id: int | None
    type: str
    severity: str
    status: str
    detail: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AlertStatusUpdate(BaseModel):
    status: str


# =========================================================
# AUDIT LOGS
# =========================================================

class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# StudentResponse references VehicleResponse (defined later in this file) -
# resolve that forward reference now that both classes exist.
StudentResponse.model_rebuild()
