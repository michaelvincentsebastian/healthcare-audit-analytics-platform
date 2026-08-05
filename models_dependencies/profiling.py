# models_dependencies/profiling.py
#
# Instrumentasi SEMENTARA untuk mengukur di mana waktu ingestion benar-benar
# habis (network vs JSON decode vs normalize vs DataFrame construction),
# sebelum memutuskan optimasi apa (misal: orjson swap, concurrency tuning,
# atau -- kalau memang terbukti perlu -- DuckDB-native parsing).
#
# DEFAULT MATI. Tidak mengubah behavior/output apa pun kalau env var
# LAKEHOUSE_PROFILE tidak di-set. Overhead saat mati cuma 1x os.getenv()
# check per proses (bukan per baris data), jadi aman ditinggal di kode.
#
# Cara pakai:
#   LAKEHOUSE_PROFILE=1 sqlmesh plan dev
#
# Setelah dapat angka yang cukup, HAPUS import + pemakaian `timed(...)` di
# frappe_client.py, extractors/common.py, dan bronze model yang dipasangi
# -- file ini sendiri boleh dihapus juga. Ini bukan bagian permanen dari
# arsitektur, murni alat ukur.
import os
import time
from contextlib import contextmanager

_ENABLED = os.getenv("LAKEHOUSE_PROFILE", "").lower() in ("1", "true", "yes")


@contextmanager
def timed(label: str):
    if not _ENABLED:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[PROFILE] {label}: {elapsed_ms:.1f} ms")
