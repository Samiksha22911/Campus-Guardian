FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

COPY requirements.txt requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Real AI models are large (multi-GB). Only install them when asked:
#   docker build --build-arg INSTALL_AI=true -t campus-guardian-api .
ARG INSTALL_AI=false
RUN if [ "$INSTALL_AI" = "true" ]; then pip install --no-cache-dir -r requirements-ai.txt; fi

COPY . .

# Note: runs as root on purpose - platform volumes mounted at /app/uploads are
# root-owned, and a non-root user could not write uploaded photos to them.

EXPOSE 8000

# Hosts like Render/Railway/Fly inject $PORT; fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
