from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai.verification_pipeline import decide, run_face_verification, run_pipeline
from ..config import settings
from ..database import get_db
from ..models import Alert, EntryLog, Gate, User, Vehicle
from ..schemas import EntryResponse, VerificationResult
from ..security import get_current_user
from ..utils import fuzzy_match_plate, normalize_plate, save_upload, write_audit_log

router = APIRouter(prefix="/api/verification", tags=["Verification"])

ALERT_TYPE_BY_STATUS = {
    "UNKNOWN_VEHICLE": "Unknown vehicle",
    "BLOCKLISTED": "Blocklisted vehicle",
    "FACE_MISMATCH": "Face mismatch",
    "MANUAL_REVIEW": "Manual review required",
}


@router.post("/process", response_model=VerificationResult)
def process_verification(
    image: UploadFile = File(...),
    gate_id: int = Form(...),
    require_face: bool = Form(default=None),
    scenario: str | None = Form(default=None),
    live: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The main AI-verification entry point.

        image -> plate detection -> OCR -> plate normalization
              -> registered-vehicle lookup (exact, then fuzzy fallback)
              -> face verification (if enabled and an owner was identified)
              -> decision
              -> entry log saved
              -> alert raised if needed
              -> result returned

    There is deliberately no vehicle-type classification AI step here (see
    the project's design decision) - `vehicle_type` in the response and in
    the saved entry log comes straight from the matched Vehicle record, or
    is null if no vehicle was matched.
    """

    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")

    image_bytes = image.file.read()
    image.file.seek(0)

    known_plates = [v.registration_number for v in db.query(Vehicle.registration_number).all()]

    pipeline_result = run_pipeline(image_bytes, known_plates=known_plates, scenario=scenario)

    # Looping-video mode: frames with no plate in them (empty road) are
    # skipped silently - they must not create entry logs or alerts.
    if live and not pipeline_result["plate_detected"]:
        return VerificationResult(
            entry_id=0, vehicle_detected=False, vehicle_type=None, plate_detected=False,
            plate_number=None, ocr_confidence=0.0, vehicle_registered=False,
            student_id=None, student_name=None, face_detected=False, face_match=None,
            face_similarity=0.0, verification_status="NO_PLATE", status="uncertain",
            rejection_reason=None, captured_image=None,
        )

    plate_number = pipeline_result["plate_number"]
    normalized_plate = normalize_plate(plate_number) if plate_number else None

    vehicle = None
    student = None
    plate_match_type = None  # "exact" | "fuzzy" | None

    if normalized_plate:
        vehicle = db.query(Vehicle).filter(Vehicle.registration_number == normalized_plate).first()
        if vehicle:
            plate_match_type = "exact"
        elif settings.PLATE_FUZZY_MATCHING:
            best_plate, _score = fuzzy_match_plate(
                normalized_plate, known_plates, threshold=settings.PLATE_FUZZY_THRESHOLD
            )
            if best_plate:
                vehicle = db.query(Vehicle).filter(Vehicle.registration_number == best_plate).first()
                plate_match_type = "fuzzy"

        if vehicle:
            student = vehicle.student

    use_face = settings.REQUIRE_FACE_VERIFICATION if require_face is None else require_face

    face_result = None
    if vehicle and student and use_face:
        face_result = run_face_verification(image_bytes, student.face_embedding, scenario=scenario)

    vehicle_registered = vehicle is not None and vehicle.status == "active"
    vehicle_blocklisted = vehicle is not None and vehicle.is_blocklisted

    simple_status, verification_status, rejection_reason = decide(
        plate_detected=pipeline_result["plate_detected"],
        ocr_confidence=pipeline_result["ocr_confidence"],
        plate_number=plate_number,
        vehicle_registered=vehicle_registered,
        vehicle_blocklisted=vehicle_blocklisted,
        require_face=use_face,
        face_result=face_result,
    )

    if vehicle is not None and not vehicle_registered and not vehicle_blocklisted:
        if vehicle.status == "pending":
            rejection_reason = "This vehicle's registration is still pending admin/security approval."
        else:
            rejection_reason = "This vehicle is currently marked inactive."

    if plate_match_type == "fuzzy" and verification_status == "GRANTED":
        rejection_reason = f"Note: matched via fuzzy plate correction (raw OCR read: {plate_number})."

    # Duplicate suppression (looping video): same plate, same gate, within the
    # window -> return the earlier result instead of logging it again.
    if live and settings.DEDUPE_WINDOW_SECONDS > 0:
        cutoff = datetime.utcnow() - timedelta(seconds=settings.DEDUPE_WINDOW_SECONDS)
        recent = (
            db.query(EntryLog)
            .filter(
                EntryLog.gate_id == gate.id,
                EntryLog.detected_plate == plate_number,
                EntryLog.decision_source == "ai",
                EntryLog.entry_time >= cutoff,
            )
            .order_by(EntryLog.entry_time.desc())
            .first()
        )
        if recent:
            return VerificationResult(
                entry_id=recent.id,
                vehicle_detected=pipeline_result["plate_detected"],
                vehicle_type=recent.detected_vehicle_type,
                plate_detected=pipeline_result["plate_detected"],
                plate_number=plate_number,
                ocr_confidence=pipeline_result["ocr_confidence"],
                vehicle_registered=recent.verification_status == "GRANTED",
                student_id=recent.student_id,
                student_name=recent.student.name if recent.student else None,
                face_detected=False, face_match=None, face_similarity=0.0,
                verification_status=recent.verification_status,
                status=recent.status,
                rejection_reason=recent.rejection_reason,
                captured_image=recent.captured_image,
                duplicate=True,
            )

    captured_image_url = None
    try:
        captured_image_url = save_upload(image, "entries", contents=image_bytes)
    except HTTPException:
        # Do not let an image-storage problem block the verification result.
        captured_image_url = None

    entry = EntryLog(
        detected_plate=plate_number,
        detected_vehicle_type=vehicle.vehicle_type if vehicle else None,
        vehicle_id=vehicle.id if vehicle else None,
        student_id=student.id if student else None,
        gate_id=gate.id,
        captured_image=captured_image_url,
        plate_confidence=pipeline_result["ocr_confidence"],
        face_confidence=face_result.get("similarity", 0.0) if face_result else 0.0,
        plate_match=vehicle is not None,
        face_match=(
            "match" if face_result and face_result.get("face_match")
            else "mismatch" if face_result and face_result.get("face_detected")
            else "not_performed"
        ),
        status=simple_status,
        verification_status=verification_status,
        rejection_reason=rejection_reason,
        decision_source="ai",
        operator_id=user.id,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    if verification_status in ("UNKNOWN_VEHICLE", "BLOCKLISTED", "FACE_MISMATCH", "MANUAL_REVIEW"):
        alert_type = ALERT_TYPE_BY_STATUS[verification_status]

        # Blocklist hits are always critical - a face match must never
        # soften this (project notes, section 24).
        severity = "critical" if verification_status == "BLOCKLISTED" else (
            "high" if verification_status in ("UNKNOWN_VEHICLE", "FACE_MISMATCH") else "medium"
        )

        # Repeated denied attempts on the same plate escalate severity.
        if verification_status == "UNKNOWN_VEHICLE" and plate_number:
            recent_denials = (
                db.query(EntryLog)
                .filter(EntryLog.detected_plate == plate_number, EntryLog.status == "denied")
                .count()
            )
            if recent_denials >= 3:
                severity = "critical"
                alert_type = "Repeated denied attempts"

        db.add(
            Alert(
                entry_id=entry.id,
                type=alert_type,
                severity=severity,
                detail=rejection_reason or alert_type,
            )
        )
        db.commit()

    write_audit_log(
        db,
        user_id=user.id,
        action="VERIFY",
        entity_type="entry_log",
        entity_id=entry.id,
        description=f"{verification_status} for plate {plate_number or 'UNREADABLE'} at gate {gate.name}",
    )

    return VerificationResult(
        entry_id=entry.id,
        vehicle_detected=pipeline_result["plate_detected"],
        vehicle_type=vehicle.vehicle_type if vehicle else None,
        plate_detected=pipeline_result["plate_detected"],
        plate_number=plate_number,
        ocr_confidence=pipeline_result["ocr_confidence"],
        vehicle_registered=vehicle_registered and not vehicle_blocklisted,
        student_id=student.id if student else None,
        student_name=student.name if student else None,
        face_detected=bool(face_result and face_result.get("face_detected")),
        face_match=face_result.get("face_match") if face_result else None,
        face_similarity=face_result.get("similarity", 0.0) if face_result else 0.0,
        verification_status=verification_status,
        status=simple_status,
        rejection_reason=rejection_reason,
        captured_image=captured_image_url,
    )


@router.get("/{entry_id}", response_model=EntryResponse)
def get_verification(entry_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    entry = db.query(EntryLog).filter(EntryLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.get("/history/list", response_model=list[EntryResponse])
def get_verification_history(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return (
        db.query(EntryLog)
        .order_by(EntryLog.entry_time.desc())
        .limit(min(limit, 500))
        .all()
    )
