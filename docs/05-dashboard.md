# 5. Dashboard (`/app/`)

## 5.1 Ringkasan

Fullstack sederhana, 1 container: **backend** (`backend/main.py`, FastAPI) +
**frontend** (`frontend/`, HTML/JS statis tanpa build step), di-serve
bersama oleh proses FastAPI yang sama. Client dari gold-server di
`/serving/` (dokumen 04) lewat protokol quack — **tidak pernah** attach
DuckLake/Postgres/MinIO langsung.

## 5.2 Struktur

```
app/
├── backend/
│   ├── main.py           -- FastAPI: /action, /health, /config.js, serve frontend statis
│   └── requirements.txt
├── frontend/
│   ├── index.html          -- Overview: summary cards, breakdown per domain, top rules
│   ├── findings.html        -- List + filter (domain/severity/status/rule_id)
│   ├── finding-detail.html   -- 1 finding: actual vs expected, rule/basis/authority, evidence
│   ├── app.js                -- fetch helper (callAction) + render helper bersama
│   └── style.css               -- palet sage green + krem
├── Dockerfile
└── docker-compose.yaml
```

## 5.3 Alur Koneksi Backend → Gold-Server

Di `lifespan()` (`app/backend/main.py`), sekali saat startup (bukan per
request):

```python
con.execute("SET threads TO 1;")   # WAJIB -- lihat §5.6
con.execute("INSTALL quack; LOAD quack;")
con.execute(f"""
    ATTACH 'quack:{QUACK_HOST}:{QUACK_PORT}' AS remote (
        TOKEN '{QUACK_SERVING_TOKEN}',
        DISABLE_SSL {QUACK_DISABLE_SSL}
    );
""")
# sanity check fail-fast:
con.execute("FROM remote.query('SELECT 1');").fetchall()
con.execute(f"SELECT 1 FROM {REMOTE_GOLD}.audit_rule LIMIT 1;").fetchall()
```

`QUACK_HOST`/`QUACK_PORT` di-override lewat `environment:` di
`app/docker-compose.yaml` ke `analytics_quack_gold_server` (nama container
gold-server) port `9494` (**port internal container**, bukan
`QUACK_SERVER_HOST_PORT` yang di-mapping ke host) — karena `dashboard` dan
`gold-server` jalan di docker network yang sama (`lakehouse-network`),
tidak perlu lewat port yang di-expose ke host sama sekali.

Kalau `ATTACH`/sanity-check gagal saat startup, proses **exit** (bukan jalan
dengan data kosong) — dikombinasikan dengan `restart: unless-stopped` di
compose, ini membuat container `dashboard` restart-loop terus sampai
gold-server hidup & reachable. Ini pengganti `depends_on` (yang tidak bisa
lintas file compose, karena `gold-server` ada di `serving/docker-compose.yaml`
yang terpisah).

## 5.4 `ACTION_REGISTRY` — Kontrak Query

Browser **tidak pernah** kirim SQL — hanya `{action, params}`. Semua SQL
didefinisikan statis di `ACTION_REGISTRY` (`main.py`), parameter selalu
di-bind pakai `?` (bukan string-building), jadi tidak ada celah SQL
injection dari sisi ini.

| Action | Dipakai di | Fungsi |
|---|---|---|
| `audit_overview` | `index.html` | Status run terkini + jumlah rule aktif/total |
| `findings_summary` | `index.html` | Total/open/under_review/resolved + breakdown severity |
| `findings_by_domain` | `index.html` | Breakdown finding per `audit_domain` |
| `top_recurring_rules` | `index.html` | Rule dengan finding terbanyak (param `limit`, default 10, max 200) |
| `list_findings` | `findings.html` | List + filter `audit_domain`/`rule_id`/`severity`/`status`, pagination `limit`/`offset` |
| `finding_detail` | `finding-detail.html` | 1 finding lengkap + JOIN info rule (`rule_name`, `rule_basis`, `authority_*`, dst) |
| `list_audit_rules` | (tersedia, belum ada halaman UI khusus) | Semua rule di registry |

Setiap entri punya `sql`, `params` (urutan bind `?`), `defaults`,
`nullable_params` (param yang boleh NULL, dipakai pola `(? IS NULL OR col =
?)` untuk filter opsional), dan `columns` (untuk mapping hasil row tuple →
dict JSON).

### Substitusi nama schema

Semua query di `ACTION_REGISTRY` ditulis literal pakai `remote.gold.<table>`
supaya SQL-nya gampang dibaca/di-diff apa adanya. Saat modul di-load, semua
kemunculan `remote.gold.` di-replace otomatis ke `remote."<GOLD_SCHEMA>".`
(`GOLD_SCHEMA` = `GOLD_SCHEMA_BASE` + `GOLD_ENV_SUFFIX`, env var yang sama
seperti di gold-server — lihat dokumen 04 §4.5). **Konsekuensi penting**:
`GOLD_ENV_SUFFIX` di `.env` root dipakai bersama oleh gold-server DAN
dashboard backend — satu sumber kebenaran, ganti environment cukup di satu
tempat.

## 5.5 Endpoint HTTP

| Endpoint | Method | Auth | Fungsi |
|---|---|---|---|
| `/action` | POST | `X-API-Token` header (`BACKEND_API_TOKEN`) | Jalankan 1 action dari `ACTION_REGISTRY` |
| `/health` | GET | Tidak | Cek `quack_connected` + `gold_reachable`, dipakai `docker compose ps`/monitoring eksternal |
| `/config.js` | GET | **Tidak (sengaja)** | Suntik `window.__API_TOKEN__` ke frontend saat runtime — lihat §5.7 |
| `/` (StaticFiles) | GET | Tidak | Serve `frontend/*.html` + asset |

Rate limiting: sliding window sederhana, **60 request/60 detik per token**,
di sisi backend (`check_rate_limit()`), berlaku untuk semua request yang
lolos autentikasi `/action`.

## 5.6 Kenapa `SET threads TO 1` — Batasan Teknis Penting

Root cause error `Multiple streaming scans ... not currently supported`:
DuckDB secara default memparalelkan operator `GROUP BY`/`JOIN` dengan
membaca sumber data dari beberapa thread scan sekaligus. Tabel
`remote.<schema>.*` di sini **bukan** file Parquet yang bisa dibaca
paralel — dia satu stream jaringan lewat quack ke gold-server, cuma bisa
dikonsumsi **satu** pembaca dalam satu waktu.

- Query **tanpa** `GROUP BY`/`JOIN` (mis. `findings_summary`,
  `audit_overview`) kebetulan tidak pernah diparalelkan DuckDB → selalu
  lolos walau `threads` tidak dibatasi.
- Query **dengan** `GROUP BY`/`JOIN` (mis. `findings_by_domain`,
  `top_recurring_rules`) dan DuckDB memutuskan paralelkan scan-nya → error.

Ini **bukan** soal race condition/concurrency antar-request (lock
`_query_lock` di §5.8 tidak menolong kasus ini) — errornya terjadi **di
dalam satu query**. `SET threads TO 1` di startup adalah fix yang benar,
bukan workaround sementara. Tidak ada trade-off performa berarti karena
beban kerja backend ini menunggu jawaban jaringan dari gold-server, bukan
komputasi CPU-berat lokal.

## 5.7 Distribusi Token Frontend — `/config.js`

`BACKEND_API_TOKEN` disuntik ke frontend saat **runtime** lewat
`GET /config.js` (bukan hardcode di file HTML statis), supaya token tidak
ikut ter-commit ke git secara tidak sengaja. Endpoint ini **publik** (tidak
lewat `authenticate()`) **sengaja** — konsumennya browser yang belum punya
token sama sekali (ayam-telur kalau dilindungi token yang sama).

⚠️ **Implikasi keamanan**: dashboard ini didesain **internal-only**.
**Jangan** expose container ke internet terbuka tanpa lapisan auth tambahan
(reverse proxy + SSO/VPN) — siapa pun yang bisa akses `/config.js` otomatis
dapat token untuk pakai `/action`.

## 5.8 Concurrency: `_query_lock`

`quack` (remote streaming scan) tidak mendukung lebih dari satu streaming
scan berjalan bersamaan lewat 1 koneksi jaringan yang sama. `con.cursor()`
per request tetap berbagi **satu** koneksi quack di bawahnya — cursor per
request **tidak cukup** untuk isolasi kalau beberapa request datang
bersamaan (mis. frontend fire beberapa action lewat `Promise.all()`,
dieksekusi FastAPI di thread berbeda).

`_query_lock` (threading.Lock) men-serialize **eksekusi query ke
gold-server** — request HTTP tetap diterima paralel oleh FastAPI, cuma
bagian yang benar-benar bicara ke quack yang digilir satu-satu.

## 5.9 Batasan Arsitektur — Hanya Baca `gold`

Backend ini **hanya** bisa membaca schema `gold` (via whitelist gold-server,
dokumen 04) — tidak ada akses ke `silver`/`bronze` sama sekali. Konsekuensi
praktis: "Applicable Records" di overview **tidak** dipecah per
Patient/Encounter — dipakai `records_scanned` dari `gold.audit_run` apa
adanya (approksimasi gabungan, lihat dokumen 03 §3.4).

## 5.10 Status Verifikasi

Yang **sudah** dilakukan (di sandbox pengembangan, tanpa Docker/network):
- `py_compile` backend.
- Tiap query `ACTION_REGISTRY` benar-benar dieksekusi terhadap skema DuckDB
  sintetis yang meniru kontrak kolom `gold.audit_rule/run/finding` asli.
- `node --check` untuk seluruh JS (`app.js` + inline script tiap halaman).

⚠️ **Belum** dites end-to-end lewat Docker + gold-server sungguhan. Ini
langkah pertama yang perlu dilakukan setelah apply ke environment nyata —
lihat checklist verifikasi di dokumen 02 §2.10.
