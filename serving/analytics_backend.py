"""
analytics_backend.py -- Proses CLIENT (backend FastAPI untuk dashboard
auditor). Sebelumnya bernama quack-server.py -- diganti nama karena
sebenarnya ini CLIENT dalam definisi Quack, bukan server. Server sungguhan
ada di quack_server.py, proses terpisah.

Prinsip keamanan yang tetap dipertahankan:
  1. Token app (BACKEND_API_TOKEN) untuk browser <-> backend ini, TERPISAH
     dari QUACK_TOKEN untuk backend <-> quack_server. Browser tidak pernah
     tahu QUACK_TOKEN.
  2. Browser tidak pernah mengirim SQL/fragmen query -- hanya {action,
     params}. SQL tetap didefinisikan di ACTION_REGISTRY, parameter selalu
     di-bind (?).
  3. Koneksi + ATTACH ke quack_server dibuat SEKALI saat startup lewat
     lifespan handler (bukan on_event yang deprecated), baru di-cursor()
     per request.
"""
import os
import time
import threading
from collections import deque, defaultdict
from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

QUACK_HOST = os.environ.get("QUACK_HOST", "127.0.0.1")
QUACK_PORT = os.environ.get("QUACK_PORT", "9494")
QUACK_TOKEN = os.environ.get("QUACK_TOKEN")
BACKEND_API_TOKEN = os.environ.get("BACKEND_API_TOKEN")
QUACK_DISABLE_SSL = os.environ.get("QUACK_DISABLE_SSL", "true").lower() == "true"

if not QUACK_TOKEN:
    raise SystemExit("QUACK_TOKEN wajib di-set -- harus sama dengan token di quack_server.py")
if not BACKEND_API_TOKEN:
    raise SystemExit("BACKEND_API_TOKEN wajib di-set -- token untuk browser/dashboard frontend")

_base_con: duckdb.DuckDBPyConnection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _base_con
    _base_con = duckdb.connect()
    _base_con.execute("INSTALL quack; LOAD quack;")

    quack_uri = f"quack:{QUACK_HOST}:{QUACK_PORT}"
    print(f"[analytics_backend] Menyambung ke Quack server di {quack_uri}...")
    _base_con.execute(f"""
        ATTACH '{quack_uri}' AS remote (
            TOKEN '{QUACK_TOKEN}',
            DISABLE_SSL {str(QUACK_DISABLE_SSL).lower()}
        );
    """)
    # Sanity check: pastikan round-trip ke server benar-benar jalan sebelum
    # backend dianggap "ready" -- gagal cepat lebih baik daripada gagal diam
    # saat request pertama dari dashboard masuk.
    _base_con.execute("FROM remote.query('SELECT 1');").fetchall()
    print("[analytics_backend] Terhubung ke Quack server. Siap menerima request.")

    yield

    print("[analytics_backend] Menutup koneksi...")
    _base_con.close()


app = FastAPI(title="Analytics Dashboard Backend (Quack client)", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo saja -- di produksi batasi ke origin frontend dashboard
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_cursor():
    """Cursor baru per request, berbagi koneksi dasar yang sudah ATTACH."""
    return _base_con.cursor()


# ---------------------------------------------------------------------------
# Rate limiting -- sliding window sederhana per token, di sisi backend.
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60
_request_log = defaultdict(deque)
_lock = threading.Lock()


def check_rate_limit(token: str):
    now = time.time()
    with _lock:
        q = _request_log[token]
        while q and now - q[0] > RATE_LIMIT_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {RATE_LIMIT_MAX_REQUESTS} requests / "
                       f"{RATE_LIMIT_WINDOW_SECONDS}s per token.",
            )
        q.append(now)


def authenticate(x_api_token: str | None):
    if x_api_token != BACKEND_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Token")
    check_rate_limit(x_api_token)


# ---------------------------------------------------------------------------
# Action registry -- satu-satunya tempat SQL didefinisikan. Query mengarah
# ke remote.lakehouse.<schema>.<table> karena quack_server.py meng-ATTACH
# DuckLake dengan nama "lakehouse". SESUAIKAN nama schema/tabel di bawah
# dengan environment SQLMesh Anda yang sesungguhnya (mis. bisa jadi
# "lakehouse.silver__prod.xxx" tergantung target environment).
# ---------------------------------------------------------------------------
ACTION_REGISTRY = {
    "list_patients": {
        "sql": """
            SELECT name, patient_name, sex, dob, status
            FROM remote.lakehouse.silver.patient_data_clean
            ORDER BY name
            LIMIT ? OFFSET ?
        """,
        "params": ["limit", "offset"],
        "defaults": {"limit": 20, "offset": 0},
        "columns": ["name", "patient_name", "sex", "dob", "status"],
    },
    "patient_encounters": {
        "sql": """
            SELECT name, patient, practitioner_name, medical_department,
                   encounter_date, status
            FROM remote.lakehouse.silver.patient_encounter_data_clean
            WHERE patient = ?
            ORDER BY encounter_date DESC
            LIMIT ? OFFSET ?
        """,
        "params": ["patient_id", "limit", "offset"],
        "defaults": {"limit": 20, "offset": 0},
        "columns": ["name", "patient", "practitioner_name", "medical_department", "encounter_date", "status"],
    },
    "encounters_per_department": {
        "sql": """
            SELECT medical_department, count(*) AS total_encounters
            FROM remote.lakehouse.silver.patient_encounter_data_clean
            WHERE encounter_date >= current_date - INTERVAL (?) DAY
            GROUP BY medical_department
            ORDER BY total_encounters DESC
        """,
        "params": ["last_n_days"],
        "defaults": {"last_n_days": 30},
        "columns": ["medical_department", "total_encounters"],
    },
}


@app.post("/action")
def run_action(
    payload: dict = Body(...),
    x_api_token: str | None = Header(default=None),
):
    authenticate(x_api_token)

    action = payload.get("action")
    spec = ACTION_REGISTRY.get(action)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    values = []
    for p in spec["params"]:
        v = payload.get("params", {}).get(p, spec["defaults"].get(p))
        if v is None:
            raise HTTPException(status_code=400, detail=f"Missing param: {p}")
        if p == "limit" and v > 100:
            raise HTTPException(status_code=400, detail="limit max 100")
        values.append(v)

    cur = get_cursor()
    rows = cur.execute(spec["sql"], values).fetchall()
    return {"action": action, "data": [dict(zip(spec["columns"], r)) for r in rows]}


@app.get("/health")
def health():
    try:
        _base_con.execute("FROM remote.query('SELECT 1');").fetchall()
        quack_ok = True
    except Exception as e:
        quack_ok = False
    return {"status": "ok" if quack_ok else "degraded", "quack_connected": quack_ok}
