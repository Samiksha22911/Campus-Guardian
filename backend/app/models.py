from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


# =========================================================
# USERS  (admin / security_officer)
# =========================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # admin | security_officer
    role: Mapped[str] = mapped_column(String(30), default="security_officer", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    entry_logs = relationship("EntryLog", back_populates="operator")
    audit_logs = relationship("AuditLog", back_populates="user")


# =========================================================
# STUDENTS
# =========================================================

class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    department: Mapped[str] = mapped_column(String(150), nullable=False)
    course: Mapped[str | None] = mapped_column(String(150), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    profile_image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Reference/placeholder for a face embedding vector (JSON-encoded string).
    # Populated by the (mocked) face enrollment step; replaced later by the
    # real embedding produced by the student's face-verification model.
    face_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

    biometric_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Set only for students who self-registered through the public student
    # portal (routers/student_portal.py) - lets them log in to check their
    # own registration/approval status. Null for students an admin/security
    # staff member entered directly (they have no self-service login).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # pending (awaiting admin/security approval - only self-registrations
    # start here) | active | inactive | rejected
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    vehicles = relationship("Vehicle", back_populates="student", cascade="all, delete-orphan")
    entry_logs = relationship("EntryLog", back_populates="student")


# =========================================================
# VEHICLES
# =========================================================

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Normalized (upper-case, no spaces) registration number - unique.
    registration_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    # Bike | Scooty | Activa | Car | Other
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)

    make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)

    vehicle_image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    owner_student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)

    # active | inactive | pending (self-registered, vehicle not yet
    # approved by staff - see routers/student_portal.py)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    is_blocklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    student = relationship("Student", back_populates="vehicles")
    entry_logs = relationship("EntryLog", back_populates="vehicle")


# =========================================================
# GATES
# =========================================================

class Gate(Base):
    __tablename__ = "gates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    camera_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    entry_logs = relationship("EntryLog", back_populates="gate")


# =========================================================
# ENTRY LOGS  (result of the verification pipeline)
# =========================================================

class EntryLog(Base):
    __tablename__ = "entry_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    detected_plate: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    detected_vehicle_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    gate_id: Mapped[int] = mapped_column(ForeignKey("gates.id"), nullable=False)

    captured_image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    plate_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    face_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    plate_match: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # match | mismatch | not_performed | unknown
    face_match: Mapped[str] = mapped_column(String(30), default="not_performed", nullable=False)

    # Simplified status used throughout the UI: granted | denied | uncertain | manual
    status: Mapped[str] = mapped_column(String(20), default="uncertain", nullable=False)

    # Detailed status from the verification pipeline, e.g. GRANTED, DENIED,
    # MANUAL_REVIEW, UNKNOWN_VEHICLE, UNKNOWN_PLATE, FACE_MISMATCH.
    verification_status: Mapped[str] = mapped_column(String(30), default="MANUAL_REVIEW", nullable=False)

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ai | manual
    decision_source: Mapped[str] = mapped_column(String(30), default="ai", nullable=False)

    entry_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    vehicle = relationship("Vehicle", back_populates="entry_logs")
    student = relationship("Student", back_populates="entry_logs")
    gate = relationship("Gate", back_populates="entry_logs")
    operator = relationship("User", back_populates="entry_logs")

    alerts = relationship("Alert", back_populates="entry", cascade="all, delete-orphan")


# =========================================================
# ALERTS
# =========================================================

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("entry_logs.id"), nullable=True)

    type: Mapped[str] = mapped_column(String(100), nullable=False)

    # low | medium | high | critical
    severity: Mapped[str] = mapped_column(String(30), default="medium", nullable=False)

    # open | acknowledged | resolved
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)

    detail: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    entry = relationship("EntryLog", back_populates="alerts")


# =========================================================
# AUDIT LOGS
# =========================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
