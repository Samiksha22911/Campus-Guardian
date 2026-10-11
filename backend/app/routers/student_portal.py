"""Public student self-registration + student portal.

Students register themselves here (no staff login required) instead of an
admin typing every record in by hand. For safety, a self-registered
student and their vehicle both start in `status="pending"` - the
verification pipeline already treats a non-"active" vehicle as
unregistered, so a pending vehicle simply cannot be used to enter campus
until a staff member reviews and approves it (see the approve/reject
endpoints in routers/students.py). This prevents someone from typing in
an arbitrary plate (including someone else's) and getting instant access.

Students who register get a password (set at registration) so they can
log into this portal and check their own status - this is a completely
separate login/token from the admin/security dashboard (routers/auth.py);
a student token can never be used against staff-only endpoints, and vice
versa (see security.py's `type` claim check).
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai.face_detector import FaceDetector
from ..ai.face_embedding import compute_embedding, serialize_embedding
from ..ai.image_utils import bytes_to_bgr
from ..config import settings
from ..database import get_db
from ..models import Student, Vehicle
from ..schemas import StudentPortalLoginRequest, StudentPortalLoginResponse, StudentResponse
from ..security import create_access_token, get_current_student, hash_password, verify_password
from ..utils import normalize_plate, save_upload

router = APIRouter(prefix="/api/student-portal", tags=["Student Portal"])


@router.post("/register", response_model=StudentPortalLoginResponse)
def register_student(
    student_id: str = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    year: int = Form(...),
    password: str = Form(..., min_length=6),
    registration_number: str = Form(...),
    vehicle_type: str = Form(...),
    course: str | None = Form(default=None),
    email: str | None = Form(default=None),
    phone: str | None = Form(default=None),
    make: str | None = Form(default=None),
    model: str | None = Form(default=None),
    color: str | None = Form(default=None),
    biometric_consent: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    student_code = student_id.strip().upper()
    plate = normalize_plate(registration_number)

    if db.query(Student).filter(Student.student_id == student_code).first():
        raise HTTPException(status_code=400, detail="A student with this student ID already exists")

    if email and db.query(Student).filter(Student.email == email).first():
        raise HTTPException(status_code=400, detail="A student with this email already exists")

    if db.query(Vehicle).filter(Vehicle.registration_number == plate).first():
        raise HTTPException(status_code=400, detail="This vehicle is already registered")

    # Validate/compute the face embedding BEFORE writing anything to the
    # database, so a bad photo never leaves behind a half-created record.
    profile_image_url = None
    face_embedding_value = None
    image_bytes = None

    if photo is not None:
        image_bytes = photo.file.read()
        photo.file.seek(0)

        if settings.MOCK_AI:
            face_embedding_value = f"mock-embedding:{student_code}"
        else:
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
                    detail="Multiple faces detected in the photo. Please upload a photo with only yourself in it.",
                )

            frame = bytes_to_bgr(image_bytes)
            x1, y1, x2, y2 = detection["bounding_box_xyxy"]
            crop = frame[y1:y2, x1:x2]
            face_embedding_value = serialize_embedding(compute_embedding(crop))

    student = Student(
        student_id=student_code,
        name=name.strip(),
        department=department.strip(),
        course=course,
        year=year,
        email=email,
        phone=phone,
        biometric_consent=biometric_consent,
        status="pending",
        password_hash=hash_password(password),
        face_embedding=face_embedding_value,
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    if photo is not None and image_bytes is not None:
        profile_image_url = save_upload(photo, "students", contents=image_bytes)
        student.profile_image = profile_image_url
        db.commit()
        db.refresh(student)

    vehicle = Vehicle(
        registration_number=plate,
        vehicle_type=vehicle_type,
        make=make,
        model=model,
        color=color,
        owner_student_id=student.id,
        status="pending",
    )
    db.add(vehicle)
    db.commit()
    db.refresh(student)

    token = create_access_token({"sub": str(student.id), "type": "student"})

    return StudentPortalLoginResponse(
        student=StudentResponse.from_model(student),
        access_token=token,
    )


@router.post("/login", response_model=StudentPortalLoginResponse)
def student_login(data: StudentPortalLoginRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == data.student_id.strip().upper()).first()

    if not student or not student.password_hash:
        raise HTTPException(
            status_code=401,
            detail="No self-service account found for that student ID. Register first, or ask "
                   "campus admin/security to enable portal login for your record.",
        )

    if not verify_password(data.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect student ID or password")

    token = create_access_token({"sub": str(student.id), "type": "student"})

    return StudentPortalLoginResponse(
        student=StudentResponse.from_model(student),
        access_token=token,
    )


@router.get("/me", response_model=StudentResponse)
def student_me(student: Student = Depends(get_current_student)):
    return StudentResponse.from_model(student)
