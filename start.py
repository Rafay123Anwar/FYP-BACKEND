#!/usr/bin/env python
"""
Production server startup for the AI ATS backend.

For development:
    uvicorn app.main:app --reload

For production (handles 100+ concurrent users):
    python start.py

Or directly:
    gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000 --timeout 60 --graceful-timeout 10 --keep-alive 5

Worker count formula: (2 x CPU cores) + 1
With 4 workers x 20 DB pool connections = 80 potential concurrent DB connections,
which comfortably handles 100 simultaneous users.
"""
import os
import subprocess
import sys

WORKERS = int(os.getenv("WEB_CONCURRENCY", "4"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

cmd = [
    sys.executable, "-m", "gunicorn",
    "app.main:app",
    "-k", "uvicorn.workers.UvicornWorker",
    "--workers", str(WORKERS),
    "--bind", f"{HOST}:{PORT}",
    "--timeout", "60",
    "--graceful-timeout", "10",
    "--keep-alive", "5",
    "--access-logfile", "-",
    "--error-logfile", "-",
]

print(f"Starting {WORKERS} uvicorn workers on {HOST}:{PORT}")
subprocess.run(cmd)
