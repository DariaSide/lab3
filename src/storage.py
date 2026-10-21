from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .config import ACCESS_KEY, BUCKET, DATA_DIR, ENDPOINT, OBJECT_KEY, REGION, RESULTS_DIR, SECRET_KEY


def client():
    return boto3.client(
        "s3", endpoint_url=ENDPOINT, aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY, region_name=REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
    )


def ensure_bucket(s3) -> None:
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)


def upload() -> dict:
    s3 = client(); ensure_bucket(s3)
    src = DATA_DIR / "devops_vacancies.ndjson"
    s3.upload_file(str(src), BUCKET, OBJECT_KEY, ExtraArgs={"ContentType": "application/x-ndjson"})
    head = s3.head_object(Bucket=BUCKET, Key=OBJECT_KEY)
    result = {"bucket": BUCKET, "key": OBJECT_KEY, "size": head["ContentLength"], "etag": head["ETag"], "endpoint": ENDPOINT}
    print(json.dumps(result, ensure_ascii=False, indent=2)); return result


def upload_results() -> list[dict]:
    s3 = client(); ensure_bucket(s3); uploaded = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        key = f"results/11-devops/{path.name}"
        s3.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": "application/json"})
        uploaded.append({"key": key, "bytes": path.stat().st_size})
    print(json.dumps(uploaded, ensure_ascii=False, indent=2)); return uploaded


def list_objects() -> list[dict]:
    s3 = client(); out = s3.list_objects_v2(Bucket=BUCKET)
    rows = [{"key": x["Key"], "size": x["Size"]} for x in out.get("Contents", [])]
    print(json.dumps(rows, ensure_ascii=False, indent=2)); return rows


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["upload", "upload-results", "list"])
    action = parser.parse_args().action
    {"upload": upload, "upload-results": upload_results, "list": list_objects}[action]()


if __name__ == "__main__": main()

