"""
Gold server: DuckDB instance yang ATTACH ke katalog DuckLake (metadata di
Postgres, data di MinIO/S3 -- persis config `gateways.duckdb.connection.catalogs.
lakehouse` di config.yaml root project), lalu expose SEMUA tabel di schema
`gold` sebagai view read-only, di-serve lewat quack_serve.

Repo ini HANYA tanggung jawab sisi gold (server). Bridge MariaDB -> bronze
ada di repo terpisah yang menempel ke Frappe app -- TIDAK disentuh/didup-
likasi di sini. Client dari server ini adalah dashboard / backend dashboard
(mis. `analytics_backend.py`) yang akan dibuat terpisah, BUKAN model bronze.

Daftar tabel gold TIDAK di-hardcode -- di-discover otomatis dari
`lakehouse.information_schema.tables WHERE table_schema = 'gold'` setiap kali
proses ini start. Alasan: schema gold masih berkembang lintas Phase 2-9 (lihat
PHASE_ROADMAP.md), jadi kalau di-hardcode akan selalu telat sync dan gampang
lupa di-update tiap ada model gold baru. Konsekuensinya: tabel gold BARU baru
ke-expose setelah container ini di-restart (tidak ada dynamic hot reload).
"""
import duckdb
import os
import sys
import signal
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("quack-gold-server")

# --- Config: koneksi ke katalog DuckLake (Postgres metadata) ---
PG_HOST = os.environ["POSTGRES_HOST"]
PG_PORT = os.environ["POSTGRES_PORT"]
PG_USER = os.environ["POSTGRES_USER"]
PG_PASSWORD = os.environ["POSTGRES_PASSWORD"]
PG_CATALOG_DB = os.environ["TABULAR_METADATA_DB_NAME"]

# --- Config: koneksi ke MinIO/S3 (data path DuckLake) ---
# MINIO_ENDPOINT (host:port, TANPA skema http://) sengaja env var terpisah
# dari MINIO_ENDPOINT_URL yang dipakai tools berbasis host (lakehouse_manager,
# dll) -- di dalam container, host MinIO BUKAN "localhost" tapi nama service
# docker (mis. "object-storage"), jadi di-override lewat docker-compose
# environment: block (lihat docker-compose.yaml), bukan lewat .env.
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "false").strip().lower() == "true"
TABULAR_BUCKET = os.environ["TABULAR_BUCKET"]

# --- Config: quack server (di-konsumsi client dashboard, mis. analytics_backend.py) ---
QUACK_BIND_HOST = os.environ.get("QUACK_BIND_HOST", "0.0.0.0")
QUACK_PORT = os.environ.get("QUACK_PORT", "9494")
# WAJIB dari env, statis -- BUKAN digenerate ulang tiap restart, supaya
# client dashboard tidak perlu baca log container tiap kali server restart.
QUACK_SERVING_TOKEN = os.environ["QUACK_SERVING_TOKEN"]
QUACK_ALLOW_OTHER_HOSTNAME = (
    os.environ.get("QUACK_ALLOW_OTHER_HOSTNAME", "true").strip().lower() == "true"
)

GOLD_SCHEMA = os.environ.get("GOLD_SCHEMA", "gold")
DUCKLAKE_CATALOG_ALIAS = "lakehouse"


def build_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL ducklake; LOAD ducklake;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL quack; LOAD quack;")

    con.execute(f"""
        CREATE OR REPLACE SECRET minio_config (
            TYPE S3,
            KEY_ID '{MINIO_ACCESS_KEY}',
            SECRET '{MINIO_SECRET_KEY}',
            ENDPOINT '{MINIO_ENDPOINT}',
            URL_STYLE 'path',
            USE_SSL {str(MINIO_USE_SSL).lower()},
            REGION 'us-east-1'
        );
    """)

    catalog_dsn = (
        f"dbname={PG_CATALOG_DB} host={PG_HOST} port={PG_PORT} "
        f"user={PG_USER} password={PG_PASSWORD}"
    )
    log.info(
        "Menyambung ke DuckLake catalog '%s' (postgres %s:%s/%s, data s3://%s/) ...",
        DUCKLAKE_CATALOG_ALIAS, PG_HOST, PG_PORT, PG_CATALOG_DB, TABULAR_BUCKET,
    )
    # READ_ONLY di level ATTACH: pertahanan pertama supaya proses ini tidak
    # bisa nulis balik ke ducklake sama sekali -- terlepas dari
    # quack_authorization_function (read_only macro) di bawah yang jadi
    # pertahanan kedua di level query yang masuk lewat quack.
    con.execute(f"""
        ATTACH 'ducklake:postgres:{catalog_dsn}' AS {DUCKLAKE_CATALOG_ALIAS}
        (DATA_PATH 's3://{TABULAR_BUCKET}/', READ_ONLY);
    """)

    # Sanity check fail-fast: ATTACH di DuckDB itu lazy, tidak benar-benar
    # membuka koneksi & memvalidasi kredensial sampai ada query yang jalan.
    con.execute(
        f"SELECT 1 FROM {DUCKLAKE_CATALOG_ALIAS}.information_schema.tables LIMIT 1"
    ).fetchone()
    log.info("Koneksi ke DuckLake catalog berhasil.")

    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{GOLD_SCHEMA}"')

    rows = con.execute(f"""
        SELECT table_name
        FROM {DUCKLAKE_CATALOG_ALIAS}.information_schema.tables
        WHERE table_schema = '{GOLD_SCHEMA}'
        ORDER BY table_name
    """).fetchall()
    gold_tables = [r[0] for r in rows]

    if not gold_tables:
        log.warning(
            "Tidak ada tabel di %s.%s.* saat ini. Normal kalau SQLMesh belum "
            "pernah `plan`/`run` untuk model gold (mis. baru Phase 1 selesai, "
            "Phase 2+ belum jalan -- lihat PHASE_ROADMAP.md). Tabel baru akan "
            "ke-expose setelah container ini di-restart.",
            DUCKLAKE_CATALOG_ALIAS, GOLD_SCHEMA,
        )

    ready, failed = 0, []
    for t in gold_tables:
        try:
            con.execute(
                f'CREATE OR REPLACE VIEW "{GOLD_SCHEMA}"."{t}" AS '
                f'SELECT * FROM {DUCKLAKE_CATALOG_ALIAS}."{GOLD_SCHEMA}"."{t}"'
            )
            # LIMIT 1, bukan count(*) -- count(*) di atas view attached lewat
            # extension eksternal (mysql/postgres/ducklake) rawan memicu bug
            # internal DuckDB terkait count_star pushdown. LIMIT 1 tetap
            # membuktikan view valid & bisa baca sampai ke storage-nya.
            row = con.execute(f'SELECT * FROM "{GOLD_SCHEMA}"."{t}" LIMIT 1').fetchone()
            status = "ada data" if row is not None else "kosong (0 baris, tapi query valid)"
            log.info("view %s.%s siap (%s)", GOLD_SCHEMA, t, status)
            ready += 1
        except Exception as e:
            log.error("GAGAL bikin view untuk tabel gold '%s': %s", t, e)
            failed.append(t)

    log.info("Ringkasan: %s/%s tabel gold ter-expose.", ready, len(gold_tables))
    if failed:
        log.warning("Tabel gold gagal di-mapping: %s", failed)

    return con


def main():
    con = build_connection()

    quack_addr = f"quack:{QUACK_BIND_HOST}:{QUACK_PORT}"
    con.execute(f"""
        CALL quack_serve('{quack_addr}',
            allow_other_hostname => {str(QUACK_ALLOW_OTHER_HOSTNAME).lower()},
            token => '{QUACK_SERVING_TOKEN}')
    """)
    con.execute(r"""
        CREATE MACRO read_only(sid, query) AS
            -- \s* di depan: DuckDB trim() TANPA argumen kedua cuma strip
            -- spasi biasa, TIDAK strip newline/tab. Query internal yang
            -- dikirim otomatis oleh quack client (mis. sinkronisasi
            -- information_schema.schemata saat ATTACH) sering diawali
            -- newline -- tanpa \s* di sini, query legit itu ke-reject.
            regexp_matches(upper(trim(query)), '^\s*(SELECT|FROM|WITH|EXPLAIN|DESCRIBE|SHOW)\b')
    """)
    con.execute("SET GLOBAL quack_authorization_function = 'read_only'")

    log.info(
        "Quack gold-server listening di %s (read-only enforced, schema=%s)",
        quack_addr, GOLD_SCHEMA,
    )

    # Wait loop yang merespons SIGTERM/SIGINT -- `input()` gagal (EOFError)
    # di container `-d` karena stdin tertutup, jadi tidak dipakai di sini.
    stop = {"flag": False}

    def _handle_signal(signum, _frame):
        log.info("Menerima signal %s, mematikan quack gold-server...", signum)
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    last_heartbeat = 0
    while not stop["flag"]:
        time.sleep(1)
        if time.time() - last_heartbeat >= 300:
            log.info("heartbeat: gold-server masih hidup")
            last_heartbeat = time.time()

    con.execute(f"CALL quack_stop('{quack_addr}')")
    log.info("Gold-server berhenti.")


if __name__ == "__main__":
    main()
