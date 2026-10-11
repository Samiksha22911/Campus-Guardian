"""Local / simple-server entry point:  python run.py

For hosted deployments you normally don't use this file - the platform runs
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
(see Dockerfile). This script exists for convenience and reads the same env
vars, so it behaves correctly in both places.
"""

import os

import uvicorn

if __name__ == "__main__":
    is_prod = os.getenv("APP_ENV", "development").lower() == "production"

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0" if is_prod else "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=not is_prod,  # auto-reload only while developing
    )
