"""
app/backend/main.py -- Backend dashboard (FastAPI). CLIENT dari gold-server
di /serving/ (lihat serving/serve.py) lewat protokol quack. Backend ini
TIDAK attach DuckLake langsung -- satu-satunya jalur ke data adalah quack
gold-server, yang sudah menegakkan read-only + hanya expose schema `gold`.

Keamanan (sama seperti desain sebelumnya, dipertahankan):
  1. Token app (BACKEND_API_TOKEN) untuk browser <-> backend ini, TERPISAH
     dari QUACK_SERVING_TOKEN untuk backend <-> gold-server. Browser tidak
     pernah tahu QUACK_SERVING_TOKEN.
  2. Browser tidak pernah kirim SQL -- hanya {action, params}. SQL didefinisikan
     di ACTION_REGISTRY, parameter selalu di-bind (?), tidak ada string-building.
  3. Koneksi + ATTACH ke gold-server dibuat SEKALI saat startup (lifespan),
     baru di-cursor() per request.

Cara backend ini menemukan gold-server: env var QUACK_HOST/QUACK_PORT. Di
docker-compose (lihat app/docker-compose.yaml), di-override ke nama container
gold-server ("analytics_quack_gold_server", port internal 9494) supaya jalan
lewat docker network `lakehouse-network` yang sama -- bukan lewat port yang
di-mapping ke host.
"""
import os
import time
import threading
from collections import deque, defaultdict
from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

QUACK_HOST = os.environ.get("QUACK_HOST", "127.0.0.1")
QUACK_PORT = os.environ.get("QUACK_PORT", "9494")
QUACK_SERVING_TOKEN = os.environ.get("QUACK_SERVING_TOKEN")
BACKEND_API_TOKEN = os.environ.get("BACKEND_API_TOKEN")
QUACK_DISABLE_SSL = os.environ.get("QUACK_DISABLE_SSL", "true").lower() == "true"

if not QUACK_SERVING_TOKEN:
    raise SystemExit("QUACK_SERVING_TOKEN wajib di-set -- harus sama dengan token di serving/.env")
if not BACKEND_API_TOKEN:
    raise SystemExit("BACKEND_API_TOKEN wajib di-set -- token untuk browser/dashboard frontend")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

_base_con: duckdb.DuckDBPyConnection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _base_con
    _base_con = duckdb.connect()
    _base_con.execute("INSTALL quack; LOAD quack;")

    quack_uri = f"quack:{QUACK_HOST}:{QUACK_PORT}"
    print(f"[app-backend] Menyambung ke gold-server di {quack_uri}...")
    _base_con.execute(f"""
        ATTACH '{quack_uri}' AS remote (
            TOKEN '{QUACK_SERVING_TOKEN}',
            DISABLE_SSL {str(QUACK_DISABLE_SSL).lower()}
        );
    """)
    # Sanity check startup: round-trip ke gold-server + schema gold benar2
    # bisa dibaca. Gagal cepat di startup lebih baik daripada baru ketahuan
    # saat request pertama dari dashboard masuk.
    _base_con.execute("FROM remote.query('SELECT 1');").fetchall()
    _base_con.execute("SELECT 1 FROM remote.gold.audit_rule LIMIT 1;").fetchall()
    print("[app-backend] Terhubung ke gold-server. Siap menerima request.")

    yield

    print("[app-backend] Menutup koneksi...")
    _base_con.close()


app = FastAPI(title="Healthcare Compliance Audit Dashboard", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dashboard internal-only -- perketat kalau di-deploy ke luar jaringan lokal
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_cursor():
    return _base_con.cursor()


# ---------------------------------------------------------------------------
# Rate limiting -- sliding window sederhana per token, sisi backend.
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX_REQUESTS = 60
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
# Action registry -- HANYA baca schema `gold` (audit_rule, audit_run,
# audit_finding), sesuai batas tanggung jawab gold-server di /serving/.
# Tidak ada akses ke silver/bronze dari backend ini sama sekali -- itu
# keputusan arsitektur di serve.py ("Repo ini HANYA tanggung jawab sisi
# gold"), bukan keterbatasan yang saya kerjakan sekitarnya di sini.
#
# Konsekuensi praktis: "Applicable Records" (jumlah pasien/encounter) di
# overview dashboard TIDAK dipecah per entitas (silver tidak terjangkau dari
# sini) -- dipakai `records_scanned` dari gold.audit_run apa adanya (approksimasi
# gabungan yang sudah dihitung di model, lihat komentar audit_run.sql).
# ---------------------------------------------------------------------------
ACTION_REGISTRY = {
    "audit_overview": {
        "sql": """
            SELECT
                r.records_scanned,
                r.rule_set_version,
                r.data_snapshot,
                r.status,
                r.started_at,
                r.finished_at,
                (SELECT count(*) FROM remote.gold.audit_rule WHERE status = 'ACTIVE') AS applicable_checks,
                (SELECT count(*) FROM remote.gold.audit_rule) AS total_rules_in_registry
            FROM remote.gold.audit_run r
        """,
        "params": [], "defaults": {}, "columns": [
            "records_scanned", "rule_set_version", "data_snapshot", "status",
            "started_at", "finished_at", "applicable_checks", "total_rules_in_registry",
        ],
    },
    "findings_summary": {
        "sql": """
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE status = 'OPEN') AS open,
                count(*) FILTER (WHERE status = 'UNDER_REVIEW') AS under_review,
                count(*) FILTER (WHERE status = 'RESOLVED') AS resolved,
                count(*) FILTER (WHERE severity = 'HIGH') AS high_severity,
                count(*) FILTER (WHERE severity = 'MEDIUM') AS medium_severity,
                count(*) FILTER (WHERE severity = 'LOW') AS low_severity
            FROM remote.gold.audit_finding
        """,
        "params": [], "defaults": {}, "columns": [
            "total", "open", "under_review", "resolved",
            "high_severity", "medium_severity", "low_severity",
        ],
    },
    "findings_by_domain": {
        "sql": """
            SELECT audit_domain, count(*) AS total_findings,
                   count(*) FILTER (WHERE status = 'OPEN') AS open_findings,
                   count(*) FILTER (WHERE severity = 'HIGH') AS high_severity_findings
            FROM remote.gold.audit_finding
            GROUP BY audit_domain
            ORDER BY total_findings DESC
        """,
        "params": [], "defaults": {}, "columns": [
            "audit_domain", "total_findings", "open_findings", "high_severity_findings",
        ],
    },
    "top_recurring_rules": {
        "sql": """
            SELECT f.rule_id, r.rule_name, r.severity, count(*) AS finding_count
            FROM remote.gold.audit_finding f
            LEFT JOIN remote.gold.audit_rule r ON r.rule_id = f.rule_id
            GROUP BY f.rule_id, r.rule_name, r.severity
            ORDER BY finding_count DESC
            LIMIT ?
        """,
        "params": ["limit"], "defaults": {"limit": 10},
        "columns": ["rule_id", "rule_name", "severity", "finding_count"],
    },
    "list_findings": {
        "sql": """
            SELECT finding_id, rule_id, audit_domain, focus_area, entity_type,
                   entity_id, patient_id, encounter_id, actual_value,
                   expected_value, severity, status, detected_at, source_system
            FROM remote.gold.audit_finding
            WHERE (? IS NULL OR audit_domain = ?)
              AND (? IS NULL OR rule_id = ?)
              AND (? IS NULL OR severity = ?)
              AND (? IS NULL OR status = ?)
            ORDER BY detected_at DESC, finding_id
            LIMIT ? OFFSET ?
        """,
        "params": [
            "audit_domain", "audit_domain", "rule_id", "rule_id",
            "severity", "severity", "status", "status", "limit", "offset",
        ],
        "defaults": {
            "audit_domain": None, "rule_id": None, "severity": None, "status": None,
            "limit": 25, "offset": 0,
        },
        "nullable_params": {"audit_domain", "rule_id", "severity", "status"},
        "columns": [
            "finding_id", "rule_id", "audit_domain", "focus_area", "entity_type",
            "entity_id", "patient_id", "encounter_id", "actual_value",
            "expected_value", "severity", "status", "detected_at", "source_system",
        ],
    },
    "finding_detail": {
        "sql": """
            SELECT f.finding_id, f.rule_id, r.rule_name, r.rule_basis,
                   r.authority_name, r.authority_reference, r.standard_name,
                   r.standard_version, f.audit_domain, f.focus_area,
                   f.entity_type, f.entity_id, f.patient_id, f.encounter_id,
                   f.actual_value, f.expected_value, f.severity, f.status,
                   f.detected_at, f.resolved_at, f.source_system,
                   f.source_record_id, f.evidence_reference, f.explanation,
                   f.reviewer_id, f.review_note, f.resolution_code
            FROM remote.gold.audit_finding f
            LEFT JOIN remote.gold.audit_rule r ON r.rule_id = f.rule_id
            WHERE f.finding_id = ?
        """,
        "params": ["finding_id"], "defaults": {},
        "columns": [
            "finding_id", "rule_id", "rule_name", "rule_basis", "authority_name",
            "authority_reference", "standard_name", "standard_version", "audit_domain",
            "focus_area", "entity_type", "entity_id", "patient_id", "encounter_id",
            "actual_value", "expected_value", "severity", "status", "detected_at",
            "resolved_at", "source_system", "source_record_id", "evidence_reference",
            "explanation", "reviewer_id", "review_note", "resolution_code",
        ],
    },
    "list_audit_rules": {
        "sql": """
            SELECT rule_id, rule_name, description, audit_domain, focus_area,
                   rule_basis, authority_name, authority_reference,
                   standard_name, standard_version, severity, status, version
            FROM remote.gold.audit_rule
            ORDER BY rule_id
        """,
        "params": [], "defaults": {}, "columns": [
            "rule_id", "rule_name", "description", "audit_domain", "focus_area",
            "rule_basis", "authority_name", "authority_reference",
            "standard_name", "standard_version", "severity", "status", "version",
        ],
    },
}


@app.post("/action")
def run_action(
    payload: dict = Body(...),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
):
    authenticate(x_api_token)

    action = payload.get("action")
    spec = ACTION_REGISTRY.get(action)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    nullable = spec.get("nullable_params", set())
    values = []
    for p in spec["params"]:
        v = payload.get("params", {}).get(p, spec["defaults"].get(p))
        if v is None and p not in nullable:
            raise HTTPException(status_code=400, detail=f"Missing param: {p}")
        if p == "limit" and v is not None and v > 200:
            raise HTTPException(status_code=400, detail="limit max 200")
        values.append(v)

    try:
        cur = get_cursor()
        rows = cur.execute(spec["sql"], values).fetchall()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Query ke gold-server gagal: {e}")

    data = [dict(zip(spec["columns"], r)) for r in rows]
    return {"action": action, "count": len(data), "data": data}


@app.get("/health")
def health():
    try:
        _base_con.execute("FROM remote.query('SELECT 1');").fetchall()
        quack_ok = True
    except Exception:
        quack_ok = False

    gold_ok = None
    if quack_ok:
        try:
            _base_con.execute("SELECT finding_id FROM remote.gold.audit_finding LIMIT 1;").fetchall()
            gold_ok = True
        except Exception:
            gold_ok = False

    status = "ok" if quack_ok and gold_ok else "degraded"
    return {"status": status, "quack_connected": quack_ok, "gold_reachable": gold_ok}


@app.get("/config.js")
def frontend_config():
    """
    Suntik BACKEND_API_TOKEN ke frontend saat runtime (bukan hardcode di file
    statis) -- supaya token tidak pernah ikut ter-commit ke git lewat
    app/frontend/*.html. Endpoint ini didaftarkan SEBELUM StaticFiles mount
    di bawah supaya path-nya tidak ke-shadow oleh static file handler.
    Route ini publik (tidak lewat authenticate()) SENGAJA -- konsumennya
    adalah browser yang belum punya token sama sekali, ayam-telur kalau
    di-lindungi token yang sama. Dashboard ini didesain internal-only (lihat
    catatan Auth di rencana implementasi) -- jangan expose container ini ke
    internet terbuka tanpa lapisan auth tambahan (mis. reverse proxy + SSO).
    """
    from fastapi.responses import Response
    return Response(
        content=f'window.__API_TOKEN__ = {BACKEND_API_TOKEN!r};',
        media_type="application/javascript",
    )


# --- Static frontend (vanilla HTML/JS, tanpa build step) ---------------------
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
