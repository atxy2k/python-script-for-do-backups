import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
import urllib.request
import urllib.parse

import boto3
from botocore.client import Config as BotoConfig


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.cfg"
TEMP_DIR = BASE_DIR / ".backup_temp"


def _to_namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


def load_config(path: Path):
    raw_text = path.read_text()
    raw_text = raw_text.strip()
    normalized = re.sub(
        r"(?m)^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:",
        lambda match: f'{match.group(1)}"{match.group(2)}":',
        raw_text,
    )
    normalized = normalized.replace("'", '"')
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
    normalized = f"{{{normalized}}}"
    data = json.loads(normalized)
    return _to_namespace(data)


def send_telegram_notification(bot_token, chat_id, message):
    """Envía una notificación a Telegram"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                print("✓ Notificación enviada a Telegram")
            else:
                print(f"✗ Error al enviar notificación: {result}")
    except Exception as e:
        print(f"✗ Error al enviar notificación a Telegram: {e}")


config = load_config(CONFIG_PATH)
filestamp = time.strftime("%Y-%m-%d-%H.%M")
backup_dir = BASE_DIR / "backup"
backup_dir.mkdir(exist_ok=True)

# Create temp directory for intermediate zips
TEMP_DIR.mkdir(exist_ok=True)

for existing_file in backup_dir.iterdir():
    if existing_file.is_file():
        existing_file.unlink()

# Clean temp directory
if TEMP_DIR.exists():
    shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()


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
        # Store extra directory zips in temp folder, not in backup/
        zip_path = TEMP_DIR / directory_object.name
        zipfolder(zip_path, target_path)
    else:
        print("Directory %s does not exist" % directory_object.path)


archive_name = f"backup_{filestamp}.zip"
archive_path = BASE_DIR / archive_name

# Create final archive with both SQL dumps and extra directory zips
with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as final_zip:
    # Add all SQL dumps from backup/
    for sql_file in backup_dir.glob("*.sql"):
        final_zip.write(sql_file, sql_file.name)
    
    # Add all extra directory zips from temp/
    for extra_zip in TEMP_DIR.glob("*.zip"):
        final_zip.write(extra_zip, extra_zip.name)

aws_region = getattr(
    config.amazon,
    "region",
    os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
)
os.environ["AWS_DEFAULT_REGION"] = aws_region
s3 = boto3.client(
    "s3",
    aws_access_key_id=config.amazon.access_key,
    aws_secret_access_key=config.amazon.secret_access,
    config=BotoConfig(signature_version="s3v4"),
    region_name=aws_region,
)

s3_current_bucket = config.amazon.bucket
s3.upload_file(str(archive_path), s3_current_bucket, archive_path.name)
download_url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": s3_current_bucket, "Key": archive_path.name},
    ExpiresIn=3600,
)

# Enviar notificación a Telegram si está configurado
if hasattr(config, 'telegram') and hasattr(config.telegram, 'bot_token') and hasattr(config.telegram, 'chat_id'):
    try:
        # Preparar información para el mensaje
        database_names = ', '.join([db.database for db in config.databases])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Obtener plantilla del mensaje o usar una por defecto
        message_template = getattr(
            config.telegram,
            'message',
            '✅ Backup completado exitosamente\n'
            '📅 Fecha: {timestamp}\n'
            '📦 Archivo: <a href="{download_url}">{filename}</a>\n'
            '💾 Bases de datos: {databases}'
        )
        
        # Reemplazar variables en el mensaje
        message = message_template.format(
            timestamp=timestamp,
            filename=archive_path.name,
            databases=database_names,
            download_url=download_url
        )
        if '{download_url}' not in message_template:
            message += (
                '\n🔗 Descargar: '
                f'<a href="{download_url}">{archive_path.name}</a>'
            )
        
        # Enviar notificación
        send_telegram_notification(
            config.telegram.bot_token,
            config.telegram.chat_id,
            message
        )
    except Exception as e:
        print(f"Warning: No se pudo enviar notificación a Telegram: {e}")

try:
    archive_path.unlink()
except OSError:
    pass

# Clean up backup/ and temp directories
for leftover_file in backup_dir.iterdir():
    if leftover_file.is_file():
        try:
            leftover_file.unlink()
        except OSError:
            pass

if TEMP_DIR.exists():
    shutil.rmtree(TEMP_DIR)