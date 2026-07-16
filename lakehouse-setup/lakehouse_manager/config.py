"""
Konfigurasi terpusat untuk Lakehouse Manager.

Semua kredensial, endpoint, dan nama resource (bucket, database) didefinisikan
di sini SAJA. Modul lain hanya boleh import dari sini, tidak boleh hardcode
ulang nilai yang sama — supaya kalau endpoint/port berubah, cukup diubah
di satu tempat.
"""

from dotenv import load_dotenv
import os

load_dotenv()

# --- Koneksi Postgres (host, dipakai untuk banyak database berbeda) ---
PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

# --- Koneksi MinIO (S3-compatible) ---
MINIO_CONFIG = {
    "endpoint_url": os.getenv("MINIO_ENDPOINT_URL"),
    "aws_access_key_id": os.getenv("MINIO_ACCESS_KEY"),
    "aws_secret_access_key": os.getenv("MINIO_SECRET_KEY"),
    "use_ssl": os.getenv("MINIO_USE_SSL").lower() == "true",
    "verify": os.getenv("MINIO_VERIFY_SSL").lower() == "true",
}

# --- Nama bucket MinIO ---
TABULAR_BUCKET = os.getenv("TABULAR_BUCKET")
UNSTRUCTURED_BUCKET = os.getenv("UNSTRUCTURED_BUCKET")

# --- Nama database Postgres ---
TABULAR_METADATA_DB_NAME = os.getenv("TABULAR_METADATA_DB_NAME")
UNSTRUCTURED_METADATA_DB_NAME = os.getenv("UNSTRUCTURED_METADATA_DB_NAME")
SQLMESH_STATE_DB_NAME = os.getenv("SQLMESH_STATE_DB_NAME")

# --- DSN untuk DuckLake ATTACH (derived, jangan diedit manual) ---
TABULAR_CONNECTION = (
    f"postgres:dbname={TABULAR_METADATA_DB_NAME} "
    f"host={PG_CONFIG['host']} user={PG_CONFIG['user']} "
    f"password={PG_CONFIG['password']} port={PG_CONFIG['port']}"
)
UNSTRUCTURED_CONNECTION = (
    f"postgres:dbname={UNSTRUCTURED_METADATA_DB_NAME} "
    f"host={PG_CONFIG['host']} user={PG_CONFIG['user']} "
    f"password={PG_CONFIG['password']} port={PG_CONFIG['port']}"
)

# --- URI bucket S3 (derived) ---
TABULAR_BUCKET_URI = f"s3://{TABULAR_BUCKET}/"
UNSTRUCTURED_BUCKET_URI = f"s3://{UNSTRUCTURED_BUCKET}/"
