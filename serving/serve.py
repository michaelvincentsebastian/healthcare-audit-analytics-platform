"""
Gold server: DuckDB instance yang ATTACH ke katalog DuckLake (metadata di
Postgres, data di MinIO/S3 -- persis config `gateways.duckdb.connection.catalogs.
lakehouse` di config.yaml root project), lalu expose tabel-tabel gold yang ada
di WHITELIST (lihat GOLD_TABLES) sebagai view read-only, di-serve lewat
quack_serve.

Repo ini HANYA tanggung jawab sisi gold (server). Bridge MariaDB -> bronze
ada di repo terpisah yang menempel ke Frappe app -- TIDAK disentuh/didup-
likasi di sini. Client dari server ini adalah dashboard / backend dashboard
(mis. `analytics_backend.py`) yang akan dibuat terpisah, BUKAN model bronze.

Daftar tabel gold yang di-serve adalah WHITELIST eksplisit (lihat GOLD_TABLES
di bawah, override-able lewat env var GOLD_TABLES tanpa perlu edit source),
BUKAN auto-discover semua isi schema gold -- tabel baru harus sengaja
ditambahkan ke whitelist dulu sebelum ke-expose ke dashboard. Nama schema
gold yang dibaca ikut konvensi virtual-environment SQLMesh: env prod = "gold"
apa adanya, env lain (mis. dev) = "gold__dev" dst, diatur lewat env var
GOLD_ENV_SUFFIX (lihat komentar di dekat definisinya). Konsekuensinya: tabel
gold BARU baru ke-expose setelah (1) ditambahkan ke whitelist dan (2)
container ini di-restart (tidak ada dynamic hot reload).
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

# --- Config: schema gold yang di-serve ---
# GOLD_ENV_SUFFIX ikut konvensi penamaan schema virtual-environment SQLMesh:
# environment prod TIDAK ada suffix (schema fisiknya persis "gold"), tapi
# environment lain (mis. hasil `sqlmesh plan dev`) di-suffix otomatis oleh
# SQLMesh jadi "gold__dev", "gold__staging", dst. Set GOLD_ENV_SUFFIX di .env
# PERSIS dengan suffix itu (termasuk "__"-nya), mis. GOLD_ENV_SUFFIX=__dev --
# kosongkan (atau jangan di-set) untuk serve dari environment prod.
GOLD_SCHEMA_BASE = os.environ.get("GOLD_SCHEMA", "gold")
GOLD_ENV_SUFFIX = os.environ.get("GOLD_ENV_SUFFIX", "__dev").strip()
GOLD_SCHEMA = f"{GOLD_SCHEMA_BASE}{GOLD_ENV_SUFFIX}"

# Daftar tabel gold yang DI-SERVE lewat quack -- WHITELIST eksplisit, BUKAN
# auto-discover lagi. Alasan ganti dari auto-discover: table baru di schema
# gold sekarang harus sengaja ditambahkan di sini (atau lewat GOLD_TABLES env,
# lihat bawah) sebelum ke-expose ke dashboard -- lebih aman daripada otomatis
# ke-expose begitu SQLMesh `run` sukses, dan kalau ada typo / tabel belum
# di-`plan` di environment ini, errornya jelas per-tabel (lihat loop di bawah)
# alih-alih diam-diam ke-skip.
#
# Bisa dioverride TOTAL lewat env var GOLD_TABLES (comma-separated), supaya
# nambah tabel gold baru ke serving tidak perlu edit source code -- cukup
# update .env lalu restart container. Kalau GOLD_TABLES tidak di-set, fallback
# ke default list di bawah.
_DEFAULT_GOLD_TABLES = ["audit_rule", 
    "audit_finding", 
    "audit_run", 
    "audit_check_identity_patient_uid_format",
    "audit_check_reference_integrity_condition_encounter",
    "audit_check_reference_integrity_observation_encounter",
    "audit_check_reference_integrity_procedure_encounter",
    "audit_check_structural_encounter_status",
    "audit_check_temporal_encounter_period",
    "audit_check_terminology_icd9cm_validity",
    "audit_check_terminology_icd10_validity"]
GOLD_TABLES = [
    t.strip()
    for t in os.environ.get("GOLD_TABLES", ",".join(_DEFAULT_GOLD_TABLES)).split(",")
    if t.strip()
]

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
    #
    # CATATAN PENTING: katalog eksternal yang di-ATTACH lewat extension
    # (ducklake, postgres, mysql, dst) TIDAK punya schema
    # "<catalog>.information_schema" sendiri -- beda dengan native DuckDB
    # catalog (mis. hasil ATTACH file .duckdb / :memory:). information_schema
    # cuma tersedia sebagai view GLOBAL di level koneksi (tanpa prefix
    # catalog), dan dia menggabungkan metadata SEMUA database yang ter-attach
    # di koneksi tsb -- makanya harus difilter pakai kolom table_catalog /
    # catalog_name, BUKAN diakses lewat "{alias}.information_schema...".
    con.execute(
        f"""
        SELECT 1 FROM information_schema.schemata
        WHERE catalog_name = '{DUCKLAKE_CATALOG_ALIAS}'
        LIMIT 1
        """
    ).fetchone()
    log.info("Koneksi ke DuckLake catalog berhasil.")

    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{GOLD_SCHEMA}"')

    # Existensi tabel di whitelist dicek dulu lewat information_schema
    # (bukan langsung CREATE VIEW) supaya tabel yang belum ada bisa dibedakan
    # dengan jelas dari tabel yang ada tapi rusak/gagal di-query -- dua kelas
    # error yang beda root cause-nya (belum di-`plan`/`run` di environment
    # ini, vs. bermasalah di storage/permission).
    rows = con.execute(f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = '{DUCKLAKE_CATALOG_ALIAS}'
          AND table_schema = '{GOLD_SCHEMA}'
    """).fetchall()
    existing = {r[0] for r in rows}

    log.info(
        "Serving %s tabel gold dari whitelist (schema %s.%s): %s",
        len(GOLD_TABLES), DUCKLAKE_CATALOG_ALIAS, GOLD_SCHEMA, GOLD_TABLES,
    )

    missing = [t for t in GOLD_TABLES if t not in existing]
    if missing:
        log.warning(
            "%s ada di whitelist GOLD_TABLES tapi BELUM ada di %s.%s -- normal "
            "kalau model gold-nya belum pernah `sqlmesh plan/run` di environment "
            "ini (GOLD_ENV_SUFFIX='%s'). Tabel ini di-skip untuk sekarang, akan "
            "ke-expose setelah ada & container di-restart.",
            missing, DUCKLAKE_CATALOG_ALIAS, GOLD_SCHEMA, GOLD_ENV_SUFFIX,
        )

    ready, failed = 0, []
    for t in GOLD_TABLES:
        if t not in existing:
            continue
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

    log.info(
        "Ringkasan: %s/%s tabel gold (dari whitelist) ter-expose (%s belum ada di catalog).",
        ready, len(GOLD_TABLES), len(missing),
    )
    if failed:
        log.warning("Tabel gold gagal di-mapping (ada di catalog tapi error): %s", failed)

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