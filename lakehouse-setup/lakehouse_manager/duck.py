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

    use_ssl_sql = "true" if config.MINIO_CONFIG["use_ssl"] else "false"

    con.execute(f"""
        CREATE OR REPLACE SECRET minio_config (
            TYPE S3,
            KEY_ID '{config.MINIO_CONFIG["aws_access_key_id"]}',
            SECRET '{config.MINIO_CONFIG["aws_secret_access_key"]}',
            ENDPOINT '{config.MINIO_S3_ENDPOINT}',
            URL_STYLE 'path',
            USE_SSL {use_ssl_sql},
            REGION 'us-east-1'
        );
    """)

    con.execute(f"SET s3_endpoint='{config.MINIO_S3_ENDPOINT}';")
    con.execute(f"SET s3_access_key_id='{config.MINIO_CONFIG['aws_access_key_id']}';")
    con.execute(f"SET s3_secret_access_key='{config.MINIO_CONFIG['aws_secret_access_key']}';")
    con.execute(f"SET s3_use_ssl={use_ssl_sql};")
    con.execute("SET s3_url_style='path';")

    return con
