"""
Operasi administratif Postgres: create/rebuild database, terminate koneksi.
Semua fungsi di sini menyentuh level *server* Postgres (bukan isi tabel).
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from . import config


def run_pg_admin_query(sql: str) -> None:
    """Jalankan satu statement admin (CREATE/DROP DATABASE) via db 'postgres'."""
    conn = psycopg2.connect(**config.PG_CONFIG, dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    try:
        cur.execute(sql)
    finally:
        cur.close()
        conn.close()


def kill_pg_connections(dbname: str) -> None:
    """Putuskan semua koneksi aktif ke sebuah database (wajib sebelum DROP)."""
    sql = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{dbname}' AND pid <> pg_backend_pid();
    """
    try:
        run_pg_admin_query(sql)
    except Exception:
        # Aman diabaikan: kemungkinan besar db belum ada / tidak ada koneksi aktif
        pass


def create_db(dbname: str) -> None:
    print(f"[*] Creating Postgres database: {dbname}...")
    try:
        run_pg_admin_query(f"CREATE DATABASE {dbname};")
        print(f"✅ Database '{dbname}' berhasil dibuat.")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✅ Database '{dbname}' sudah tersedia.")
        else:
            print(f"❌ Gagal membuat {dbname}: {e}")


def rebuild_db(dbname: str) -> None:
    """DROP + CREATE ulang database, lalu bersihkan schema public dari sisa constraint."""
    print(f"[*] Rebuilding database: {dbname}...")
    try:
        kill_pg_connections(dbname)
        run_pg_admin_query(f"DROP DATABASE IF EXISTS {dbname};")
        run_pg_admin_query(f"CREATE DATABASE {dbname};")

        conn = psycopg2.connect(**config.PG_CONFIG, dbname=dbname)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        cur.execute("GRANT ALL ON SCHEMA public TO public;")
        cur.close()
        conn.close()
        print(f"✅ Database '{dbname}' bersih dari constraint.")
    except Exception as e:
        print(f"❌ Gagal rebuild {dbname}: {e}")
