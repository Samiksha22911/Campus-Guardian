Put your trained model weights here:

- `plate_best.pt` - from `ai/train_plate_yolo.py` (see project root)
- `face_best.pt`  - from `ai/train_face_yolo.py` (see project root)

Both paths are configurable via `PLATE_MODEL_PATH` / `FACE_MODEL_PATH` in
`backend/.env` if you'd rather keep them elsewhere. Neither file is
required while `MOCK_AI=true`.
