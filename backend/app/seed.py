"""Populate the database with demo data so the application can be tested
immediately after setup.

Run with:  python -m app.seed   (from the backend/ directory, venv active)

This seeds a small, CURATED set of 8 students (rather than a large random
batch) so every branch of the decision matrix (project notes, section 20)
has a deterministic, easy-to-demo example:

    STU2001  Aditi Sharma      -> normal active vehicle          -> GRANTED path
    STU2002  Rohan Mehta       -> normal active vehicle          -> GRANTED path
    STU2003  Priya Nair        -> normal active vehicle          -> GRANTED path
    STU2004  Karan Verma       -> normal active vehicle          -> GRANTED path
    STU2005  Sneha Iyer        -> normal active vehicle          -> GRANTED path
    STU2006  Arjun Malhotra    -> vehicle is BLOCKLISTED         -> BLOCKLIST_ALERT path
    STU2007  Divya Kulkarni    -> vehicle active, NO face on file-> FACE UNAVAILABLE path
    STU2008  Manish Rathore    -> vehicle marked INACTIVE        -> denied (inactive) path
    STU2009  Neha Kapoor       -> SELF-REGISTERED, awaiting approval -> demos the student portal
                                   (login student_id=STU2009 / password=Student@123 at
                                   POST /api/student-portal/login, and the staff approval
                                   flow at GET /api/students/pending)

Use the verification endpoint's `scenario` parameter (or an OCR reading of
an unregistered plate, e.g. "MP99ZZ0000") to exercise UNKNOWN_VEHICLE,
FACE_MISMATCH, and OCR/manual-review paths against these same records.

Every seeded student gets a synthetic placeholder avatar (a plain colored
initial, generated with Pillow - see backend/uploads/students/demo/) as
`profile_image`, NOT a real photo of any real person. `face_embedding` is
left as the same mock placeholder string the app has always used
(MOCK_AI mode doesn't read it) UNLESS you run `python -m app.enroll_demo_faces`
after switching to real mode, which computes real embeddings from photos
you provide - see that script's docstring.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Alert, EntryLog, Gate, Student, User, Vehicle
from .security import hash_password
from .utils import normalize_plate

DEMO_STUDENTS = [
    # student_id, name,             department,                    course,   year, plate,        vehicle_type, blocklisted, active, has_face
    ("STU2001", "Aditi Sharma",     "Computer Science",             "B.Tech", 3, "MP07AB1234", "Car",   False, True,  True),
    ("STU2002", "Rohan Mehta",      "Electronics & Communication",  "B.Tech", 2, "MP09XY5678", "Bike",  False, True,  True),
    ("STU2003", "Priya Nair",       "Mechanical Engineering",       "B.Tech", 4, "MP04CD5566", "Scooty",False, True,  True),
    ("STU2004", "Karan Verma",      "Information Technology",       "B.Tech", 1, "MP12EF7788", "Car",   False, True,  True),
    ("STU2005", "Sneha Iyer",       "Civil Engineering",            "B.Tech", 3, "MP15GH9900", "Bike",  False, True,  True),
    ("STU2006", "Arjun Malhotra",   "Electrical Engineering",       "B.Tech", 2, "MP03IJ2233", "Car",   True,  True,  True),
    ("STU2007", "Divya Kulkarni",   "Computer Science",             "B.Tech", 1, "MP18KL4455", "Scooty",False, True,  False),
    ("STU2008", "Manish Rathore",   "Information Technology",       "B.Tech", 4, "MP21MN6677", "Bike",  False, False, True),
]

BLOCK_REASON = "Reported for repeated unauthorized parking in the faculty zone"


def seed_database():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # =====================================================
        # USERS
        # =====================================================

        users = [
            {"name": "Campus Admin", "email": "admin@campus.edu", "password": "Admin@123", "role": "admin"},
            {"name": "Security Officer - Priya", "email": "guard1@campus.edu", "password": "Guard@123", "role": "security_officer"},
            {"name": "Security Officer - Aman", "email": "guard2@campus.edu", "password": "Guard@123", "role": "security_officer"},
        ]

        for item in users:
            existing = db.query(User).filter(User.email == item["email"]).first()
            if not existing:
                db.add(User(
                    name=item["name"],
                    email=item["email"],
                    password_hash=hash_password(item["password"]),
                    role=item["role"],
                ))

        db.commit()

        # =====================================================
        # GATES
        # =====================================================

        gates = [
            {"name": "Main Gate", "location": "Front Entrance", "camera_id": "MAIN_CAM_01"},
            {"name": "Vehicle Gate", "location": "Vehicle Entrance", "camera_id": "VEH_CAM_01"},
            {"name": "Hostel Gate", "location": "Hostel Entrance", "camera_id": "HOSTEL_CAM_01"},
        ]

        for item in gates:
            existing = db.query(Gate).filter(Gate.name == item["name"]).first()
            if not existing:
                db.add(Gate(name=item["name"], location=item["location"], camera_id=item["camera_id"]))

        db.commit()

        # =====================================================
        # STUDENTS + VEHICLES (curated, deterministic - see module docstring)
        # =====================================================

        if db.query(Student).count() == 0:
            students = []
            vehicles = []

            for student_id, name, department, course, year, plate, vtype, blocklisted, active, has_face in DEMO_STUDENTS:
                first_name = name.split()[0].lower()
                student = Student(
                    student_id=student_id,
                    name=name,
                    email=f"{first_name}.{student_id.lower()}@campus.edu",
                    phone=f"9{abs(hash(student_id)) % 900000000 + 100000000}",
                    department=department,
                    course=course,
                    year=year,
                    biometric_consent=True,
                    status="active",
                    profile_image=f"/uploads/students/demo/{student_id.lower()}.png",
                )
                if has_face:
                    # Placeholder only - see module docstring re: real embeddings.
                    student.face_embedding = f"mock-embedding:{student_id}"

                db.add(student)
                students.append(student)

            db.commit()
            for s in students:
                db.refresh(s)

            for row, student in zip(DEMO_STUDENTS, students):
                _student_id, _name, _department, _course, _year, plate, vtype, blocklisted, active, _has_face = row
                vehicle = Vehicle(
                    registration_number=normalize_plate(plate),
                    vehicle_type=vtype,
                    make="Honda" if vtype in ("Bike", "Scooty") else "Maruti Suzuki",
                    model="Activa" if vtype == "Scooty" else ("Splendor" if vtype == "Bike" else "Swift"),
                    color="Black",
                    owner_student_id=student.id,
                    status="active" if active else "inactive",
                    is_blocklisted=blocklisted,
                    block_reason=BLOCK_REASON if blocklisted else None,
                )
                db.add(vehicle)
                vehicles.append(vehicle)

            db.commit()
            for v in vehicles:
                db.refresh(v)

            # =====================================================
            # STU2009 - a SELF-REGISTERED student awaiting approval,
            # demonstrating the student-portal registration flow (see
            # routers/student_portal.py). Unlike the 8 above, this one has
            # a password_hash (so it can log into the student portal) and
            # starts in "pending" status, same as a real self-registration
            # would, until a staff member approves it.
            # =====================================================

            pending_student = Student(
                student_id="STU2009",
                name="Neha Kapoor",
                email="neha.stu2009@campus.edu",
                phone="9876543210",
                department="Computer Science",
                course="B.Tech",
                year=2,
                biometric_consent=True,
                status="pending",
                password_hash=hash_password("Student@123"),
            )
            db.add(pending_student)
            db.commit()
            db.refresh(pending_student)

            pending_vehicle = Vehicle(
                registration_number=normalize_plate("MP22OP8899"),
                vehicle_type="Bike",
                make="Honda",
                model="Shine",
                color="Blue",
                owner_student_id=pending_student.id,
                status="pending",
            )
            db.add(pending_vehicle)
            db.commit()

            # =====================================================
            # SAMPLE ENTRY LOGS (last 3 days) - illustrates each outcome
            # =====================================================

            all_gates = db.query(Gate).all()
            main_gate = all_gates[0]
            now = datetime.utcnow()

            def _entry_time(days_ago, hour):
                return now - timedelta(days=days_ago, hours=(now.hour - hour) % 24)

            sample_entries = []

            # A few clean GRANTED entries for the first five students.
            for i, (student, vehicle) in enumerate(zip(students[:5], vehicles[:5])):
                sample_entries.append(EntryLog(
                    detected_plate=vehicle.registration_number,
                    detected_vehicle_type=vehicle.vehicle_type,
                    vehicle_id=vehicle.id,
                    student_id=student.id,
                    gate_id=all_gates[i % len(all_gates)].id,
                    plate_confidence=0.9 + i * 0.01,
                    face_confidence=0.85 + i * 0.02,
                    plate_match=True,
                    face_match="match",
                    status="granted",
                    verification_status="GRANTED",
                    rejection_reason=None,
                    decision_source="ai",
                    entry_time=_entry_time(i % 3, 8 + i),
                ))

            # STU2006 - blocklisted vehicle attempts entry -> BLOCKLIST alert.
            blocklisted_vehicle = vehicles[5]
            entry_block = EntryLog(
                detected_plate=blocklisted_vehicle.registration_number,
                detected_vehicle_type=blocklisted_vehicle.vehicle_type,
                vehicle_id=blocklisted_vehicle.id,
                student_id=students[5].id,
                gate_id=main_gate.id,
                plate_confidence=0.95,
                face_confidence=0.0,
                plate_match=True,
                face_match="not_performed",
                status="denied",
                verification_status="BLOCKLISTED",
                rejection_reason=f"Plate {blocklisted_vehicle.registration_number} is on the blocklist.",
                decision_source="ai",
                entry_time=_entry_time(0, 9),
            )
            sample_entries.append(entry_block)

            # STU2007 - no face on file yet -> manual review.
            no_face_vehicle = vehicles[6]
            entry_no_face = EntryLog(
                detected_plate=no_face_vehicle.registration_number,
                detected_vehicle_type=no_face_vehicle.vehicle_type,
                vehicle_id=no_face_vehicle.id,
                student_id=students[6].id,
                gate_id=main_gate.id,
                plate_confidence=0.91,
                face_confidence=0.0,
                plate_match=True,
                face_match="not_performed",
                status="uncertain",
                verification_status="MANUAL_REVIEW",
                rejection_reason="No face detected for verification.",
                decision_source="ai",
                entry_time=_entry_time(1, 10),
            )
            sample_entries.append(entry_no_face)

            # STU2008 - vehicle inactive -> denied.
            inactive_vehicle = vehicles[7]
            entry_inactive = EntryLog(
                detected_plate=inactive_vehicle.registration_number,
                detected_vehicle_type=inactive_vehicle.vehicle_type,
                vehicle_id=inactive_vehicle.id,
                student_id=students[7].id,
                gate_id=main_gate.id,
                plate_confidence=0.93,
                face_confidence=0.0,
                plate_match=True,
                face_match="not_performed",
                status="denied",
                verification_status="UNKNOWN_VEHICLE",
                rejection_reason="This vehicle is currently marked inactive.",
                decision_source="ai",
                entry_time=_entry_time(2, 11),
            )
            sample_entries.append(entry_inactive)

            # An unregistered plate -> UNKNOWN_VEHICLE.
            entry_unknown = EntryLog(
                detected_plate="MP99ZZ0000",
                detected_vehicle_type=None,
                vehicle_id=None,
                student_id=None,
                gate_id=main_gate.id,
                plate_confidence=0.88,
                face_confidence=0.0,
                plate_match=False,
                face_match="not_performed",
                status="denied",
                verification_status="UNKNOWN_VEHICLE",
                rejection_reason="Plate MP99ZZ0000 is not registered.",
                decision_source="ai",
                entry_time=_entry_time(0, 14),
            )
            sample_entries.append(entry_unknown)

            # An OCR failure -> manual review.
            entry_ocr_fail = EntryLog(
                detected_plate=None,
                detected_vehicle_type=None,
                gate_id=main_gate.id,
                plate_confidence=0.0,
                face_confidence=0.0,
                plate_match=False,
                face_match="not_performed",
                status="uncertain",
                verification_status="MANUAL_REVIEW",
                rejection_reason="Number plate could not be detected.",
                decision_source="ai",
                entry_time=_entry_time(1, 16),
            )
            sample_entries.append(entry_ocr_fail)

            for e in sample_entries:
                db.add(e)
            db.commit()
            for e in sample_entries:
                db.refresh(e)

            # =====================================================
            # ALERTS for the non-granted entries above
            # =====================================================

            db.add(Alert(
                entry_id=entry_block.id, type="Blocklisted vehicle", severity="critical",
                detail=entry_block.rejection_reason,
            ))
            db.add(Alert(
                entry_id=entry_no_face.id, type="Manual review required", severity="medium",
                detail=entry_no_face.rejection_reason,
            ))
            db.add(Alert(
                entry_id=entry_inactive.id, type="Unknown vehicle", severity="high",
                detail=entry_inactive.rejection_reason,
            ))
            db.add(Alert(
                entry_id=entry_unknown.id, type="Unknown vehicle", severity="high",
                detail=entry_unknown.rejection_reason,
            ))
            db.commit()

        print("Database seeded successfully.")
        print(f"  {len(DEMO_STUDENTS)} students / vehicles covering every decision-matrix outcome.")
        print("  + STU2009 (Neha Kapoor) - a pending self-registration for demoing the student portal.")
        print("Demo staff logins:")
        for item in users:
            print(f"  {item['role']:<18} {item['email']:<28} {item['password']}")
        print("Demo student-portal login:")
        print(f"  {'student':<18} {'STU2009':<28} Student@123")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
