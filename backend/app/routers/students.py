from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..ai.face_detector import FaceDetector
from ..ai.face_embedding import compute_embedding, serialize_embedding
from ..ai.image_utils import bytes_to_bgr
from ..config import settings
from ..database import get_db
from ..models import Student, User, Vehicle
from ..schemas import StudentCreate, StudentRejectRequest, StudentResponse, StudentUpdate
from ..security import get_current_user, require_roles
from ..utils import save_upload, write_audit_log

router = APIRouter(prefix="/api/students", tags=["Students"])


@router.get("", response_model=list[StudentResponse])
def get_students(
    search: str | None = None,
    department: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Student)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Student.name.ilike(like), Student.student_id.ilike(like), Student.email.ilike(like))
        )

    if department:
        query = query.filter(Student.department == department)

    if status_filter:
        query = query.filter(Student.status == status_filter)

    students = query.order_by(Student.created_at.desc()).all()
    return [StudentResponse.from_model(s) for s in students]


@router.get("/pending", response_model=list[StudentResponse])
def get_pending_students(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Students who self-registered through the public student portal and
    are awaiting approval - see routers/student_portal.py. Both staff
    roles can review these (security staff are the ones actually manning
    the gate, so they need to be able to act on these too, not just admin)."""
    students = (
        db.query(Student)
        .filter(Student.status == "pending")
        .order_by(Student.created_at.asc())
        .all()
    )
    return [StudentResponse.from_model(s) for s in students]


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return StudentResponse.from_model(student)


@router.post("", response_model=StudentResponse)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    student_code = data.student_id.strip().upper()

    existing = db.query(Student).filter(Student.student_id == student_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student ID already exists")

    if data.email:
        existing_email = db.query(Student).filter(Student.email == data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="A student with this email already exists")

    student = Student(
        student_id=student_code,
        name=data.name.strip(),
        department=data.department.strip(),
        course=data.course,
        year=data.year,
        email=data.email,
        phone=data.phone,
        biometric_consent=data.biometric_consent,
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    write_audit_log(
        db,
        user_id=user.id,
        action="CREATE",
        entity_type="student",
        entity_id=student.id,
        description=f"Registered student {student.student_id} ({student.name})",
    )

    return StudentResponse.from_model(student)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    updates = data.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'inactive'")

    for field, value in updates.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    write_audit_log(
        db,
        user_id=user.id,
        action="UPDATE",
        entity_type="student",
        entity_id=student.id,
        description=f"Updated student {student.student_id}: {list(updates.keys())}",
    )

    return StudentResponse.from_model(student)


@router.delete("/{student_id}")
def deactivate_student(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Soft delete - deactivate rather than physically remove, preserving
    # entry-log history and referential integrity.
    student.status = "inactive"
    db.commit()

    write_audit_log(
        db,
        user_id=user.id,
        action="DEACTIVATE",
        entity_type="student",
        entity_id=student.id,
        description=f"Deactivated student {student.student_id}",
    )

    return {"message": "Student deactivated"}


@router.post("/{student_id}/photo", response_model=StudentResponse)
def upload_student_photo(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    image_bytes = file.file.read()
    file.file.seek(0)

    url = save_upload(file, "students", contents=image_bytes)
    student.profile_image = url

    if settings.MOCK_AI:
        # Mock face enrollment: store a lightweight placeholder "embedding"
        # so the (mocked) face-verification stage has something to compare
        # against.
        student.face_embedding = f"mock-embedding:{student.student_id}"
    else:
        # Real enrollment: detect the face in the uploaded photo and store
        # its actual embedding vector (JSON-encoded) - this is the
        # "Retrieve Owner Face" reference that later gate verifications get
        # compared against (see project notes, section 14 & 17).
        try:
            detection = FaceDetector().detect(image_bytes)
        except NotImplementedError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        if not detection["face_detected"]:
            raise HTTPException(
                status_code=400,
                detail="No face detected in the uploaded photo. Please upload a clear, front-facing photo.",
            )
        if detection.get("multiple_faces"):
            raise HTTPException(
                status_code=400,
                detail="Multiple faces detected in the uploaded photo. Please upload a photo with only the student's face.",
            )

        frame = bytes_to_bgr(image_bytes)
        x1, y1, x2, y2 = detection["bounding_box_xyxy"]
        crop = frame[y1:y2, x1:x2]

        vector = compute_embedding(crop)
        student.face_embedding = serialize_embedding(vector)

    db.commit()
    db.refresh(student)

    write_audit_log(
        db,
        user_id=user.id,
        action="FACE_ENROLL",
        entity_type="student",
        entity_id=student.id,
        description=f"Uploaded profile photo / face reference for {student.student_id}",
    )

    return StudentResponse.from_model(student)


@router.post("/{student_id}/approve", response_model=StudentResponse)
def approve_student(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    """Approves a self-registered student (routers/student_portal.py) and
    activates their pending vehicle(s), letting the vehicle actually pass
    verification from now on."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.status != "pending":
        raise HTTPException(status_code=400, detail=f"Student is not pending approval (status: {student.status})")

    student.status = "active"

    pending_vehicles = db.query(Vehicle).filter(
        Vehicle.owner_student_id == student.id, Vehicle.status == "pending"
    ).all()
    for vehicle in pending_vehicles:
        vehicle.status = "active"

    db.commit()
    db.refresh(student)

    write_audit_log(
        db,
        user_id=user.id,
        action="APPROVE",
        entity_type="student",
        entity_id=student.id,
        description=f"Approved self-registered student {student.student_id} ({student.name}) "
                     f"and {len(pending_vehicles)} pending vehicle(s)",
    )

    return StudentResponse.from_model(student)


@router.post("/{student_id}/reject", response_model=StudentResponse)
def reject_student(
    student_id: int,
    data: StudentRejectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    """Rejects a self-registered student. Their pending vehicle(s) are
    marked inactive rather than deleted, preserving the record for audit
    purposes."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.status != "pending":
        raise HTTPException(status_code=400, detail=f"Student is not pending approval (status: {student.status})")

    student.status = "rejected"

    pending_vehicles = db.query(Vehicle).filter(
        Vehicle.owner_student_id == student.id, Vehicle.status == "pending"
    ).all()
    for vehicle in pending_vehicles:
        vehicle.status = "inactive"

    db.commit()
    db.refresh(student)

    write_audit_log(
        db,
        user_id=user.id,
        action="REJECT",
        entity_type="student",
        entity_id=student.id,
        description=f"Rejected self-registered student {student.student_id} ({student.name})"
                     + (f": {data.reason}" if data.reason else ""),
    )

    return StudentResponse.from_model(student)
