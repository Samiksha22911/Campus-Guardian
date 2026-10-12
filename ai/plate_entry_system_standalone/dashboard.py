"""
dashboard.py
-------------
Simple Streamlit web UI for the college gate system - good for a project
demo/viva. Upload a photo of a vehicle, see the detected plate box, the
OCR reading, and whether entry is allowed, plus a running log table.

Run with:
    streamlit run dashboard.py -- --weights runs_plate/plate_yolo11/weights/best.pt
"""

import sys
import argparse
import cv2
import numpy as np
import pandas as pd
import streamlit as st

from plate_detector import PlateDetector
from ocr_reader import PlateOCR
from database import init_db, check_plate, log_entry, get_connection


@st.cache_resource
def load_models(weights_path: str, device: str):
    detector = PlateDetector(weights_path, conf_threshold=0.4, device=device)
    ocr = PlateOCR(gpu=(device != "cpu"))
    return detector, ocr


def get_recent_logs(limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM entry_logs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return pd.DataFrame([dict(r) for r in rows])


def main():
    # Parse the --weights flag passed after `streamlit run dashboard.py --`
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(sys.argv[1:])

    init_db()
    st.set_page_config(page_title="College Gate - Plate Recognition", layout="wide")
    st.title("College Vehicle Entry System")
    st.caption("YOLOv11 plate detection + OCR, matched against the registered vehicle database")

    detector, ocr = load_models(args.weights, args.device)

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded = st.file_uploader("Upload a photo of the vehicle (gate camera snapshot)",
                                     type=["jpg", "jpeg", "png"])
        if uploaded:
            file_bytes = np.frombuffer(uploaded.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            detections = detector.detect(frame)
            texts = []
            for det in detections:
                plate_text, ocr_conf = ocr.read_plate(det.crop)
                texts.append(plate_text)

                if not plate_text:
                    st.warning("Plate detected but text could not be read clearly.")
                    continue

                result = check_plate(plate_text)
                log_entry(plate_text, result)

                if result.allowed:
                    owner = result.record.owner_name if result.record else "Unknown"
                    st.success(f"ALLOWED — Plate: {plate_text}  |  Matched: {result.matched_plate}  "
                               f"|  Owner: {owner}  |  Match similarity: {result.similarity:.2f}")
                else:
                    st.error(f"DENIED — Plate: {plate_text}  |  Not found in registry "
                             f"(closest similarity: {result.similarity:.2f})")

            annotated = detector.draw_boxes(frame, detections, texts)
            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption="Detection result")

    with col2:
        st.subheader("Recent entry log")
        df = get_recent_logs()
        if df.empty:
            st.info("No entries logged yet.")
        else:
            st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
