FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

# System libs OpenCV / torch need at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ai-plate.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Real plate AI (YOLO + EasyOCR). Set to false to build the small mock-only image:
#   docker build --build-arg INSTALL_AI=false .
ARG INSTALL_AI=true
RUN if [ "$INSTALL_AI" = "true" ]; then \
      pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir -r requirements-ai-plate.txt && \
      python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"; \
    fi

COPY . .

# Note: runs as root on purpose - platform volumes mounted at /app/uploads are
# root-owned, and a non-root user could not write uploaded photos to them.

EXPOSE 8000

# Hosts like Render/Railway/Fly inject $PORT; fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
