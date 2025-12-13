import json
import os
import re
import subprocess
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import boto3
from botocore.client import Config as BotoConfig


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.cfg"


def _to_namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


def load_config(path: Path):
    raw_text = path.read_text()
    raw_text = raw_text.strip()
    normalized = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", r'"\1":', raw_text)
    normalized = normalized.replace("'", '"')
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
    normalized = f"{{{normalized}}}"
    data = json.loads(normalized)
    return _to_namespace(data)


config = load_config(CONFIG_PATH)
filestamp = time.strftime("%Y-%m-%d-%H.%M")
backup_dir = BASE_DIR / "backup"
backup_dir.mkdir(exist_ok=True)

for existing_file in backup_dir.iterdir():
    if existing_file.is_file():
        existing_file.unlink()


def run_mysqldump(database, destination: Path):
    dump_cmd = [
        "mysqldump",
        f"--user={database.user}",
        f"--password={database.password}",
        f"--host={database.host}",
        f"--port={database.port}",
        "--single-transaction",
        "--set-gtid-purged=OFF",
        "-e",
        "--opt",
        "-c",
        database.database,
    ]
    with destination.open("w") as dump_file:
        subprocess.check_call(dump_cmd, stdout=dump_file)


for database in config.databases:
    dump_path = backup_dir / f"{database.database}_{filestamp}.sql"
    run_mysqldump(database, dump_path)


def zipfolder(zip_path, target_dir):
    zip_path = Path(zip_path)
    if zip_path.suffix != ".zip":
        zip_path = zip_path.with_suffix(".zip")

    target_dir = Path(target_dir)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipobj:
        rootlen = len(str(target_dir)) + 1
        for base, _, files in os.walk(target_dir):
            for file in files:
                fn = os.path.join(base, file)
                zipobj.write(fn, fn[rootlen:])


for directory_object in config.extra_directories:
    target_path = Path(directory_object.path)
    if target_path.exists():
        zip_path = backup_dir / directory_object.name
        zipfolder(zip_path, target_path)
    else:
        print("Directory %s does not exist" % directory_object.path)


archive_name = f"backup_{filestamp}.zip"
archive_path = BASE_DIR / archive_name

zipfolder(archive_path, backup_dir)

aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
s3 = boto3.client(
    "s3",
    aws_access_key_id=config.amazon.access_key,
    aws_secret_access_key=config.amazon.secret_access,
    config=BotoConfig(signature_version="s3v4"),
    region_name=aws_region,
)

s3_current_bucket = config.amazon.bucket
s3.upload_file(str(archive_path), s3_current_bucket, archive_path.name)

try:
    archive_path.unlink()
except OSError:
    pass
