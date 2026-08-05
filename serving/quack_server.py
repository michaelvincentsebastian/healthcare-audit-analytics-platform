"""
quack_server.py -- Proses SERVER (sisi lakehouse).

Ini SATU-SATUNYA proses yang boleh ATTACH langsung ke DuckLake (Postgres
sebagai katalog metadata, MinIO sebagai storage). Semua client (termasuk
analytics_backend.py) tidak pernah menyentuh Postgres/MinIO secara langsung
-- mereka bicara ke proses ini lewat protokol Quack.

Kenapa dipisah jadi proses sendiri (bukan bagian dari FastAPI backend):
  1. Quack server dan Quack client itu dua peran yang berbeda secara teknis.
     Server = yang memanggil quack_serve(). Client = yang ATTACH/quack_query
     ke URI itu. Menggabungkan keduanya dalam satu proses tidak salah secara
     teknis, tapi memisahkannya berarti backend FastAPI Anda tidak perlu tahu
     apa pun soal Postgres/MinIO -- kalau kredensial storage berubah, cukup
     restart proses ini, backend tidak perlu di-deploy ulang.
  2. Proses server ini juga bisa dipakai client LAIN di masa depan (notebook
     analisis ad-hoc, dashboard kedua, dbt/SQLMesh run) tanpa masing-masing
     perlu attach ke Postgres/MinIO sendiri-sendiri.

Cara jalan:
  quack_serve() TIDAK blocking -- dia mendaftarkan listener lalu langsung
  return. Karena itu proses ini punya loop keep-alive di akhir, dan proses
  ini HARUS tetap hidup (systemd service), bukan script sekali-jalan.

Env var yang dipakai (selain yang sudah ada di lakehouse_manager/config.py):
  QUACK_BIND_HOST     default "0.0.0.0"  -- interface yang didengarkan
  QUACK_PORT          default "9494"
  QUACK_TOKEN         WAJIB diisi (bukan digenerate otomatis), supaya token
                      yang sama bisa dipakai konsisten oleh client tanpa
                      copy-paste manual tiap restart. Simpan di secret
                      manager / .env yang tidak masuk git, JANGAN hardcode.
  QUACK_ALLOW_OTHER_HOSTNAME  default "true" jika client bukan di localhost
                      yang sama dengan server.
"""
import os
import signal
import sys
import threading

import duckdb

# Reuse konfigurasi Postgres/MinIO yang sudah ada, jangan duplikasi.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lakehouse-setup"))
from lakehouse_manager import config  # noqa: E402

QUACK_BIND_HOST = os.environ.get("QUACK_BIND_HOST", "0.0.0.0")
QUACK_PORT = os.environ.get("QUACK_PORT", "9494")
QUACK_TOKEN = os.environ.get("QUACK_TOKEN")
QUACK_ALLOW_OTHER_HOSTNAME = os.environ.get("QUACK_ALLOW_OTHER_HOSTNAME", "true").lower() == "true"

if not QUACK_TOKEN or len(QUACK_TOKEN) < 4:
    raise SystemExit(
        "QUACK_TOKEN wajib di-set (minimal 4 karakter) sebagai env var. "
        "Jangan biarkan Quack generate token acak -- client butuh nilai "
        "yang stabil untuk disimpan sebagai secret."
    )

QUACK_URI = f"quack:{QUACK_BIND_HOST}:{QUACK_PORT}"

_shutdown_event = threading.Event()
_con: duckdb.DuckDBPyConnection | None = None


def _build_connection() -> duckdb.DuckDBPyConnection:
    """Sama persis pola get_duckdb_connection() di duck.py -- ATTACH ke
    DuckLake (Postgres + MinIO) sekali di proses ini. Client tidak pernah
    lihat langkah ini."""
    con = duckdb.connect()
    con.execute("INSTALL ducklake; LOAD ducklake;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL quack; LOAD quack;")  # core extension sejak DuckDB 1.5.3

    con.execute(f"""
        CREATE OR REPLACE SECRET minio_config (
            TYPE S3,
            KEY_ID '{config.MINIO_CONFIG["aws_access_key_id"]}',
            SECRET '{config.MINIO_CONFIG["aws_secret_access_key"]}',
            ENDPOINT '{config.MINIO_CONFIG["endpoint_url"]}',
            URL_STYLE 'path',
            USE_SSL {str(config.MINIO_CONFIG["use_ssl"]).lower()},
            REGION 'us-east-1'
        );
    """)

    # Katalog DuckLake yang sama seperti dipakai SQLMesh (lihat config.yaml:
    # gateways.duckdb.connection.catalogs.lakehouse) -- di-ATTACH dengan nama
    # "lakehouse" supaya client bisa query lakehouse.silver.<table> dst.
    con.execute(f"""
        ATTACH '{config.TABULAR_CONNECTION}' AS lakehouse (
            TYPE ducklake,
            DATA_PATH '{config.TABULAR_BUCKET_URI}'
        );
    """)

    return con


def main() -> None:
    global _con
    print(f"[quack_server] Menyiapkan koneksi DuckLake...")
    _con = _build_connection()

    print(f"[quack_server] Membuka listener di {QUACK_URI} "
          f"(allow_other_hostname={QUACK_ALLOW_OTHER_HOSTNAME})")
    result = _con.execute(f"""
        SELECT * FROM quack_serve(
            '{QUACK_URI}',
            token := '{QUACK_TOKEN}',
            allow_other_hostname := {str(QUACK_ALLOW_OTHER_HOSTNAME).lower()}
        );
    """).fetchall()
    print(f"[quack_server] Server siap. Detail: {result}")
    print(f"[quack_server] Client harus ATTACH ke: quack:<host-server-ini>:{QUACK_PORT}")

    def _handle_shutdown(signum, frame):
        print(f"[quack_server] Menerima signal {signum}, mematikan server...")
        _shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    # quack_serve() tidak blocking -- proses ini WAJIB tetap hidup, kalau
    # tidak, listener ikut mati begitu fungsi main() selesai.
    _shutdown_event.wait()

    print("[quack_server] Menghentikan quack_serve dan menutup koneksi...")
    try:
        _con.execute(f"SELECT quack_stop('{QUACK_URI}');")
    except Exception as e:
        print(f"[quack_server] quack_stop gagal (mungkin sudah berhenti): {e}")
    _con.close()
    print("[quack_server] Selesai.")


if __name__ == "__main__":
    main()