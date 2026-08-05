"""
Macro untuk ambil QUACK_TOKEN dari environment variable, supaya token
tidak pernah hardcode di SQL model manapun / ke-commit ke git.

Taruh QUACK_TOKEN=... di file .env di root project lakehouse (JANGAN di
config.yaml -- config.yaml biasanya ikut ke-commit ke git).

load_dotenv() dipanggil di sini sendiri (bukan cuma andalkan shell
export manual) -- supaya macro tetap jalan benar terlepas dari
bagaimana `sqlmesh plan/run` dipanggil (CLI langsung, cron, systemd,
dsb). Konsisten dengan pola fix load_dotenv() di analytics_backend.py.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmesh import macro

# Cari .env mulai dari lokasi file ini naik ke root project, supaya
# tetap ketemu meskipun sqlmesh dipanggil dari subdirectory mana pun.
for parent in Path(__file__).resolve().parents:
    candidate = parent / ".env"
    if candidate.exists():
        load_dotenv(candidate)
        break


@macro()
def quack_token(evaluator):
    try:
        token = os.environ["QUACK_SOURCE_TOKEN"]
    except KeyError:
        raise RuntimeError(
            "QUACK_TOKEN tidak ditemukan di environment. "
            "Pastikan ada baris QUACK_TOKEN=... di file .env root lakehouse."
        )
    return f"'{token}'"
