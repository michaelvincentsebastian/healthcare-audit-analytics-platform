# Dashboard (Phase 7)

Fullstack: `backend/main.py` (FastAPI, client quack ke gold-server di `../serving/`) +
`frontend/` (HTML/JS statis, di-serve oleh backend yang sama, tanpa build step).

## Prasyarat

1. `../` (root project) `.env` sudah terisi nilai asli (bukan placeholder) untuk minimal:
   `QUACK_SERVING_TOKEN`, `BACKEND_API_TOKEN`, `LAKEHOUSE_CONNECTION_NETWORK`.
2. Root `docker-compose.yaml` (Postgres + MinIO) sudah `up`, network
   `lakehouse-network` sudah ada.
3. `../serving/` (gold-server) sudah `docker compose up -d` **duluan** dan sehat
   (`docker compose ps` menunjukkan healthy) — kalau belum, `dashboard` akan
   terus restart-loop (lihat komentar di `docker-compose.yaml`).
4. `sqlmesh plan`/`run` sudah pernah dijalankan minimal sampai Phase 5 (`gold.audit_rule`,
   `gold.audit_run`, `gold.audit_finding` sudah punya data) — kalau belum, dashboard tetap
   jalan tapi semua angka 0 / tabel kosong (bukan error).

## Jalankan

```bash
cd app
docker compose up -d --build
```

Buka `http://localhost:8000` (atau `DASHBOARD_HOST_PORT` kalau di-override di `.env`).

## Struktur

```
app/
├── backend/
│   ├── main.py          -- FastAPI: /action (ACTION_REGISTRY, gold-only), /health, serve frontend statis
│   └── requirements.txt
├── frontend/
│   ├── index.html        -- Overview: summary cards, domain breakdown, top rules, cakupan audit
│   ├── findings.html      -- List + filter (domain/severity/status/rule_id)
│   ├── finding-detail.html -- 1 finding: actual vs expected, rule/basis/authority, evidence
│   ├── app.js             -- fetch helper + render helper bersama
│   └── style.css           -- palet warna dari referensi desain (sage green + krem)
├── Dockerfile
└── docker-compose.yaml
```

## Yang PERLU Anda tahu / batasan sengaja

- Backend ini **hanya** bisa membaca schema `gold` (audit_rule/audit_run/audit_finding) --
  sesuai batas tanggung jawab gold-server di `/serving/`. Tidak ada akses ke silver/bronze.
  Konsekuensinya, "Applicable Records" di overview tidak dipecah per Patient/Encounter --
  pakai `records_scanned` dari `gold.audit_run` apa adanya (sudah gabungan, lihat komentar
  di `audit_run.sql`).
- Token dashboard (`BACKEND_API_TOKEN`) disuntik ke frontend saat runtime lewat
  `GET /config.js` (bukan hardcode di file statis) supaya tidak ke-commit ke git secara
  tidak sengaja. Endpoint ini publik (tanpa token) by design -- dashboard ini internal-only,
  JANGAN expose container ke internet terbuka tanpa reverse proxy + auth tambahan.
- Verifikasi yang sudah dilakukan: `py_compile` backend, tiap query `ACTION_REGISTRY`
  benar-benar dieksekusi terhadap skema DuckDB sintetis yang meniru kontrak kolom
  `gold.audit_rule/run/finding` asli, dan `node --check` untuk seluruh JS (app.js + inline
  script tiap halaman). **Belum** dites end-to-end lewat Docker + gold-server sungguhan
  (tidak tersedia di sandbox saya) -- test itu jadi langkah pertama Anda setelah apply.
