"""Face embedding model.

Uses a pretrained FaceNet (InceptionResnetV1, VGGFace2 weights) via the
facenet-pytorch package purely for *inference* - there is no training step
for this part, unlike the two YOLO detectors. It converts a face crop into
a 512-dimensional vector; two vectors from the same person's face end up
close together in that space, which is what face_verification.py compares.

This intentionally mirrors the project notes' separation of concerns:
face_detector.py answers "where is a face in this frame?", this module
answers "turn that face into a comparable vector", and face_verification.py
decides "is this vector close enough to the expected owner's vector?".
"""

import json

import numpy as np

_model_singleton = None


def _get_model():
    """Lazy-load the embedding model once per process."""
    global _model_singleton
    if _model_singleton is None:
        from facenet_pytorch import InceptionResnetV1
        _model_singleton = InceptionResnetV1(pretrained="vggface2").eval()
    return _model_singleton


def compute_embedding(face_crop_bgr: np.ndarray) -> list[float]:
    """face_crop_bgr: an OpenCV BGR array containing (ideally just) a face,
    as produced by FaceDetector.detect(). Returns a plain Python list of
    floats so it can be JSON-serialized and stored in the database."""
    import cv2
    import torch

    model = _get_model()

    face = cv2.resize(face_crop_bgr, (160, 160))
    face_rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

    tensor = torch.from_numpy(face_rgb).permute(2, 0, 1).float()
    tensor = (tensor - 127.5) / 128.0  # normalize to roughly [-1, 1], as facenet-pytorch expects
    tensor = tensor.unsqueeze(0)

    with torch.no_grad():
        embedding = model(tensor)[0].numpy()

    return embedding.tolist()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Returns a 0..1 similarity score (not raw cosine [-1, 1]) so it lines
    up with the same 0..1 scale used everywhere else in the app
    (MIN_FACE_CONFIDENCE, the mock service's 'similarity', etc.)."""
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)

    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0

    cosine = float(np.dot(a, b) / denom)
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0))


def serialize_embedding(vector: list[float]) -> str:
    return json.dumps(vector)


def deserialize_embedding(raw: str | None) -> list[float] | None:
    """Returns None (rather than raising) for empty values or for legacy
    mock placeholder strings like 'mock-embedding:STU1001', so callers can
    treat 'no real embedding on file yet' as a single clean case."""
    if not raw or not raw.strip().startswith("["):
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
