"""
Operasi terhadap object storage (MinIO / S3-compatible).
"""

import boto3
from botocore.exceptions import ClientError

from . import config

# Satu client dibuat sekali saat modul di-import, dipakai ulang oleh semua fungsi
s3_client = boto3.client("s3", **config.MINIO_CONFIG)


def create_minio_bucket(bucket_name: str) -> None:
    print(f"[*] Checking MinIO bucket: {bucket_name}...")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' sudah ada.")
    except ClientError as e:
        if e.response["Error"]["Code"] in ["404", "403"]:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' berhasil dibuat.")
        else:
            print(f"❌ Error MinIO: {e}")
