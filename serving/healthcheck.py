"""
Dipanggil oleh Docker HEALTHCHECK untuk gold-server. Exit 0 = sehat, exit
!= 0 = unhealthy.

Sengaja TIDAK probe tabel gold tertentu -- di awal-awal phase (lihat
PHASE_ROADMAP.md) schema gold bisa saja masih kosong tapi server-nya sendiri
tetap sehat. `SELECT 1` cukup untuk menguji jalur penuh: quack server ->
DuckDB session -> ducklake extension -> Postgres catalog masih hidup (kalau
attach ducklake gagal, server tidak akan pernah lolos start-up, jadi kalau
proses ini masih bisa dikontak berarti attach sudah sukses).
"""
import os
import sys
import duckdb

TOKEN = os.environ["QUACK_SERVING_TOKEN"]
HOST = os.environ.get("QUACK_BIND_HOST_LOCAL", "localhost")
PORT = os.environ.get("QUACK_PORT", "9494")

try:
    con = duckdb.connect()
    con.execute("INSTALL quack; LOAD quack;")
    con.execute(f"""
        FROM quack_query(
            'quack:{HOST}:{PORT}',
            'SELECT 1',
            token = '{TOKEN}',
            disable_ssl => true
        )
    """).fetchall()
    sys.exit(0)
except Exception as e:
    print(f"healthcheck failed: {e}", file=sys.stderr)
    sys.exit(1)
