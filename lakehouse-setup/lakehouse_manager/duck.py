"""
Pembuatan koneksi DuckDB yang sudah siap pakai: extension (ducklake, postgres,
httpfs) ter-load, dan credential S3/MinIO ter-set sebagai secret.
"""

import duckdb

from . import config


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL ducklake; LOAD ducklake;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL httpfs; LOAD httpfs;")

    con.execute(f"""
        CREATE OR REPLACE SECRET minio_config (
            TYPE S3,
            KEY_ID '{config.MINIO_CONFIG["aws_access_key_id"]}',
            SECRET '{config.MINIO_CONFIG["aws_secret_access_key"]}',
            ENDPOINT 'localhost:9000',
            URL_STYLE 'path',
            USE_SSL false,
            REGION 'us-east-1'
        );
    """)

    con.execute("SET s3_endpoint='localhost:9000';")
    con.execute(f"SET s3_access_key_id='{config.MINIO_CONFIG['aws_access_key_id']}';")
    con.execute(f"SET s3_secret_access_key='{config.MINIO_CONFIG['aws_secret_access_key']}';")
    con.execute("SET s3_use_ssl=false;")
    con.execute("SET s3_url_style='path';")

    return con
