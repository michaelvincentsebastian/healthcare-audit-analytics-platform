"""
Definisi & pembuatan skema tabel untuk katalog metadata unstructured.
Kalau nanti ada tabel katalog lain (mis. audit_log, ingestion_run), tambahkan
fungsi baru di sini — jangan campur dengan orchestrator.py.
"""

import psycopg2

from . import config


def create_unstructured_metadata_table_format() -> None:
    """Buat tabel 'unstructured_metadata' di database katalog unstructured (idempotent)."""
    print("[*] Membuat tabel 'unstructured_metadata'")
    con = None
    cur = None
    try:
        con = psycopg2.connect(
            host=config.PG_CONFIG["host"],
            port=config.PG_CONFIG["port"],
            dbname=config.UNSTRUCTURED_METADATA_DB_NAME,
            user=config.PG_CONFIG["user"],
            password=config.PG_CONFIG["password"],
        )
        con.autocommit = True
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS unstructured_metadata (
                id              UUID,
                file_name       TEXT,
                file_extension  TEXT,
                file_size       BIGINT,
                content_type    TEXT,
                title           TEXT,
                description     TEXT,
                source          TEXT,
                tags            JSON,
                uploaded_by     TEXT,
                bucket          TEXT,
                object_key      TEXT,
                minio_url       TEXT,
                upload_status   TEXT,
                ingested_at     TIMESTAMPTZ
            );
        """)
        print("✅ Tabel 'unstructured_metadata' siap.")
    except Exception as e:
        print(f"❌ Gagal membuat tabel 'unstructured_metadata': {e}")
    finally:
        if cur:
            cur.close()
        if con:
            con.close()
            print("Koneksi database ditutup.")
