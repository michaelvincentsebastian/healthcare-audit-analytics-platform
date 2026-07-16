"""
Orkestrasi: menggabungkan storage + pg_admin + duck + catalog menjadi satu
alur setup end-to-end. Modul ini TIDAK berisi logic detail — hanya memanggil
fungsi dari modul lain secara berurutan. Kalau ada error di sini, cek dulu
apakah errornya sebenarnya berasal dari salah satu modul yang dipanggil.
"""

from . import config
from .storage import create_minio_bucket
from .pg_admin import create_db
from .duck import get_duckdb_connection
from .catalog import create_unstructured_metadata_table_format


def datalakehouse_initial_setup() -> None:
    print("\n--- Starting Full Initial Setup ---")

    create_minio_bucket(config.TABULAR_BUCKET)
    create_minio_bucket(config.UNSTRUCTURED_BUCKET)

    create_db(config.TABULAR_METADATA_DB_NAME)
    create_db(config.UNSTRUCTURED_METADATA_DB_NAME)
    create_db(config.SQLMESH_STATE_DB_NAME)

    con = None
    try:
        con = get_duckdb_connection()
        print("[*] Attaching DuckLake to Postgres...")

        con.execute(
            f"ATTACH 'ducklake:{config.TABULAR_CONNECTION}' AS lakehouse "
            f"(DATA_PATH '{config.TABULAR_BUCKET_URI}');"
        )
        con.execute(
            f"ATTACH 'ducklake:{config.UNSTRUCTURED_CONNECTION}' AS metadata_catalog "
            f"(DATA_PATH '{config.UNSTRUCTURED_BUCKET_URI}');"
        )

        print("✅ Datalakehouse initial setup completed successfully!")
    except Exception as e:
        print(f"❌ Error during DuckDB Attach: {e}")
        if "constraints are not supported" in str(e):
            print(
                "\n💡 TIP: Masalah Constraint DuckLake terdeteksi. "
                "Silakan pilih opsi 3 untuk Rebuild Metadata DB."
            )
    finally:
        if con:
            con.close()

    create_unstructured_metadata_table_format()
