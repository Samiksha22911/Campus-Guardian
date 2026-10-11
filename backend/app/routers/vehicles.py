from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student, User, Vehicle
from ..schemas import VehicleCreate, VehicleResponse, VehicleUpdate
from ..security import get_current_user, require_roles
from ..utils import normalize_plate, save_upload, write_audit_log

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])

VEHICLE_TYPES = {"Bike", "Scooty", "Activa", "Car", "Other"}


@router.get("", response_model=list[VehicleResponse])
def get_vehicles(
    search: str | None = None,
    vehicle_type: str | None = None,
    status_filter: str | None = None,
    blocklisted: bool | None = None,
    owner_student_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Vehicle)

    if search:
        query = query.filter(Vehicle.registration_number.ilike(f"%{normalize_plate(search)}%"))

    if vehicle_type:
        query = query.filter(Vehicle.vehicle_type == vehicle_type)

    if status_filter:
        query = query.filter(Vehicle.status == status_filter)

    if blocklisted is not None:
        query = query.filter(Vehicle.is_blocklisted == blocklisted)

    if owner_student_id is not None:
        query = query.filter(Vehicle.owner_student_id == owner_student_id)

    return query.order_by(Vehicle.created_at.desc()).all()


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.post("", response_model=VehicleResponse)
def create_vehicle(
    data: VehicleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    student = db.query(Student).filter(Student.id == data.owner_student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Owner student not found")

    if data.vehicle_type not in VEHICLE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"vehicle_type must be one of {sorted(VEHICLE_TYPES)}",
        )

    plate = normalize_plate(data.registration_number)
    if not plate:
        raise HTTPException(status_code=400, detail="A valid registration number is required")

    existing = db.query(Vehicle).filter(Vehicle.registration_number == plate).first()
    if existing:
        raise HTTPException(status_code=400, detail="This registration number is already registered")

    vehicle = Vehicle(
        registration_number=plate,
        vehicle_type=data.vehicle_type,
        make=data.make,
        model=data.model,
        color=data.color,
        owner_student_id=data.owner_student_id,
    )

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    write_audit_log(
        db,
        user_id=user.id,
        action="CREATE",
        entity_type="vehicle",
        entity_id=vehicle.id,
        description=f"Registered vehicle {vehicle.registration_number} for student {student.student_id}",
    )

    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    updates = data.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'inactive'")

    if "vehicle_type" in updates and updates["vehicle_type"] not in VEHICLE_TYPES:
        raise HTTPException(status_code=400, detail=f"vehicle_type must be one of {sorted(VEHICLE_TYPES)}")

    for field, value in updates.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)

    write_audit_log(
        db,
        user_id=user.id,
        action="UPDATE",
        entity_type="vehicle",
        entity_id=vehicle.id,
        description=f"Updated vehicle {vehicle.registration_number}: {list(updates.keys())}",
    )

    return vehicle


@router.delete("/{vehicle_id}")
def deactivate_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicle.status = "inactive"
    db.commit()

    write_audit_log(
        db,
        user_id=user.id,
        action="DEACTIVATE",
        entity_type="vehicle",
        entity_id=vehicle.id,
        description=f"Deactivated vehicle {vehicle.registration_number}",
    )

    return {"message": "Vehicle deactivated"}


@router.post("/{vehicle_id}/photo", response_model=VehicleResponse)
def upload_vehicle_photo(
    vehicle_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "security_officer")),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicle.vehicle_image = save_upload(file, "vehicles")
    db.commit()
    db.refresh(vehicle)
    return vehicle
