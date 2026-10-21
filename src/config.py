from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "artifacts"
RESULTS_DIR = ARTIFACTS_DIR / "results"
LOG_DIR = ARTIFACTS_DIR / "run-logs"

ENDPOINT = os.getenv("RUSTFS_ENDPOINT", "http://localhost:9000")
ACCESS_KEY = os.getenv("RUSTFS_ACCESS_KEY", "LAB3ACCESSKEY")
SECRET_KEY = os.getenv("RUSTFS_SECRET_KEY", "Lab3SecretKeyChangeMe2026")
BUCKET = os.getenv("RUSTFS_BUCKET", "hh-lake")
REGION = os.getenv("RUSTFS_REGION", "us-east-1")
OBJECT_KEY = "variants/11-devops/vacancies.ndjson"
ROLE = "DevOps-инженер"

for directory in (DATA_DIR, RESULTS_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)

