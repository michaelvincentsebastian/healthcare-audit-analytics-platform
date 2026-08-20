"""
Antarmuka CLI (menu interaktif). Modul ini hanya urusan I/O dengan user dan
routing pilihan menu ke fungsi di modul lain — tidak ada logic bisnis di sini.
"""

import time

from . import config
from .storage import create_minio_bucket
from .pg_admin import create_db, rebuild_db
from .catalog import create_unstructured_metadata_table_format
from .orchestrator import datalakehouse_initial_setup

MENU = """
=============================================
      PLATY LAKEHOUSE MANAGER (v2.1)
=============================================
1. Create MinIO Buckets (lake + metadata)
2. Create DuckLake Metadata Database (Postgres)
3. REBUILD DuckLake Metadata Database (Fix Constraints)
4. Create SQLMesh State Database (Postgres)
5. REBUILD SQLMesh State Database
6. Create unstructure_metadata Catalog + Schema
7. REBUILD unstructure_metadata Catalog + Schema
8. RUN FULL INITIAL SETUP
---------------------------------------------
Type 'exit' to quit program
"""


# --- Setiap pilihan menu punya fungsi sendiri yang jelas namanya ---
# (bukan lambda satu baris) supaya gampang di-debug/di-trace satu-satu.

def _action_create_buckets() -> None:
    create_minio_bucket(config.TABULAR_BUCKET)
    create_minio_bucket(config.UNSTRUCTURED_BUCKET)


def _action_create_tabular_db() -> None:
    create_db(config.TABULAR_METADATA_DB_NAME)


def _action_rebuild_tabular_db() -> None:
    rebuild_db(config.TABULAR_METADATA_DB_NAME)


def _action_create_sqlmesh_db() -> None:
    create_db(config.SQLMESH_STATE_DB_NAME)


def _action_rebuild_sqlmesh_db() -> None:
    rebuild_db(config.SQLMESH_STATE_DB_NAME)


def _action_create_unstructured_catalog() -> None:
    create_minio_bucket(config.UNSTRUCTURED_BUCKET)
    create_db(config.UNSTRUCTURED_METADATA_DB_NAME)
    create_unstructured_metadata_table_format()


def _action_rebuild_unstructured_catalog() -> None:
    create_minio_bucket(config.UNSTRUCTURED_BUCKET)
    rebuild_db(config.UNSTRUCTURED_METADATA_DB_NAME)
    create_unstructured_metadata_table_format()


ACTIONS = {
    "1": _action_create_buckets,
    "2": _action_create_tabular_db,
    "3": _action_rebuild_tabular_db,
    "4": _action_create_sqlmesh_db,
    "5": _action_rebuild_sqlmesh_db,
    "6": _action_create_unstructured_catalog,
    "7": _action_rebuild_unstructured_catalog,
    "8": datalakehouse_initial_setup,
}


def run_auto() -> None:
    """
    Mode non-interaktif untuk automation (dipanggil dari `docker compose up`).
    Logic-nya SAMA PERSIS dengan opsi menu 8 (RUN FULL INITIAL SETUP), hanya
    saja tanpa loop `input()` supaya bisa jalan sebagai container yang
    exit sendiri begitu setup selesai.
    """
    print(MENU)
    print(">> [AUTO MODE] Running option 8: RUN FULL INITIAL SETUP\n")
    datalakehouse_initial_setup()


def run() -> None:
    while True:
        print(MENU)
        choice = input(">> Select choice: ").strip().lower()

        if choice == "exit":
            print("👋 Exiting program...")
            break

        action = ACTIONS.get(choice)
        if action:
            action()
        else:
            print("⚠️ Invalid option. Please try again.")

        time.sleep(1)
        input("\n[Press Enter to return to menu]")
