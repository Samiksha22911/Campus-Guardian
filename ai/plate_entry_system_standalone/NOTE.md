# Note

This is the original standalone plate-detection + OCR + SQLite project
(built before Campus Guardian's face-verification layer existed). It's
kept here for reference and for isolated component testing per the "test
each part separately before integrating" strategy - it is NOT wired into
the FastAPI backend.

The actual, integrated version of this logic now lives in
`backend/app/ai/plate_detector.py` and `backend/app/ai/ocr_service.py`,
with a MySQL/SQLite (SQLAlchemy) vehicle registry instead of this folder's
plain `database.py` - see the main project README for how those connect
into the full Campus Guardian pipeline (plate -> OCR -> DB -> face -> decision).

You can still run this standalone project on its own (see its README.md)
if you just want to sanity-check plate detection + OCR on some test images
without booting the whole backend.
