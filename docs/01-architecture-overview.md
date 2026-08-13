# 1. Architecture Overview

## 1.1 Ringkasan Satu Paragraf

Project ini adalah **lakehouse compliance-audit** untuk data SatuSehat (rekam
medis elektronik, format FHIR) yang berasal dari sistem RME berbasis
**Frappe** (backend PHP-like/Python framework, data disimpan di **MariaDB**).
Data mengalir lewat 3 layer medallion (**bronze → silver → gold**) yang
dikelola **SQLMesh**, disimpan sebagai **DuckLake** (katalog Postgres + data
Parquet di **MinIO/S3**), lalu hasil akhirnya (`gold.audit_*`) di-serve ke
**dashboard web internal** lewat protokol **quack** (remote DuckDB).

## 1.2 Batas Repo — PENTING

Project ini **bukan satu repo tunggal**. Ada 2 repo yang saling terhubung
lewat jaringan (bukan lewat kode yang di-share):

| Repo | Isi | Ada di dokumentasi ini? |
|---|---|---|
| **[`rakhaafd/clinic-satusehat`](https://github.com/rakhaafd/clinic-satusehat)** — app Frappe utama, sumber data | Aplikasi RME klinik (Frappe app, `clinic_satusehat`, MariaDB sebagai storage-nya) — ini **sumber data utama** seluruh pipeline. Bronze-bridge (DuckDB instance yang ATTACH ke MariaDB dan expose tabel raw lewat `quack_serve` di port `9494`) hidup menempel ke app ini. | **Tidak** — di luar scope repo ini, cuma disebut sebagai sumber data eksternal. Repo-nya standar scaffold Frappe app (`bench get-app`/`bench install-app`), README publiknya belum mendokumentasikan detail bronze-bridge secara eksplisit — kalau butuh detail exact lokasi script bridge-nya, cek langsung ke repo tsb atau tanya pemegangnya. |
| **Repo ini** (`lakehouse`) | SQLMesh project (bronze/silver/gold models), gold-server (`/serving/`), dashboard (`/app/`), infra Postgres+MinIO. | Ya, seluruhnya. |

Konsekuensi paling penting dari pemisahan ini: **model bronze di repo ini
adalah CLIENT dari bronze-bridge di `clinic-satusehat`**, bukan yang
menjalankan bridge itu. `sqlmesh run` di repo ini akan gagal kalau
bronze-bridge di `clinic-satusehat` tidak sedang jalan dan reachable di
`quack:localhost:9494` (atau host lain sesuai `QUACK_URI` yang dipakai macro
`quack_token()`).

## 1.3 Diagram Alur Data End-to-End

```
┌───────────────────────────────────────┐
│  clinic-satusehat (Frappe app, repo    │
│  terpisah: github.com/rakhaafd/        │
│  clinic-satusehat) -- SUMBER DATA UTAMA│
│                                         │
│  MariaDB (raw data klinik/RME)         │
│         │                              │
│         ▼                              │
│  bronze-bridge (quack_serve)           │
│  quack:<host>:9494                     │
└──────────────┬──────────────────────────┘
               │ ATTACH 'quack:...' (models/frappe/bronze/*.sql,
               │ macro @quack_token() dari QUACK_SOURCE_TOKEN)
               ▼
┌──────────────────────────────────────────────────────────────┐
│  REPO INI (lakehouse) -- dikelola SQLMesh, disimpan di        │
│  DuckLake (katalog Postgres "metadata-catalog" + data di      │
│  MinIO "object-storage", bucket s3://tabular/)                │
│                                                                │
│  bronze.*  (models/frappe/bronze/*.sql, kind INCREMENTAL)     │
│      │  raw, 1:1 mapping dari MariaDB, explicit column cast   │
│      ▼                                                        │
│  silver.*  (models/frappe/silver/*.sql)                       │
│      │  dibersihkan, di-flatten dari FHIR ndjson (flatquack)  │
│      ▼                                                        │
│  gold.audit_rule / audit_run / audit_finding                  │
│  (models/frappe/gold/audit/*.sql, lihat dokumen 03)           │
│      │  hasil evaluasi 8 rule compliance aktif                │
│      ▼                                                        │
│  serving/serve.py -- "gold-server"                            │
│  ATTACH ducklake:postgres:... -> expose WHITELIST tabel gold  │
│  lewat quack_serve di quack:<host>:9494 (port INTERNAL        │
│  container, mapping host default 9495 -- lihat dokumen 04)    │
│      │  ATTACH 'quack:...' (app/backend/main.py)              │
│      ▼                                                        │
│  app/backend/main.py -- FastAPI, ACTION_REGISTRY (read-only,  │
│  parametrized SQL saja, tidak ada raw SQL dari browser)        │
│      │  HTTP + header X-API-Token (BACKEND_API_TOKEN)         │
│      ▼                                                        │
│  app/frontend/*.html -- dashboard (overview, findings, detail)│
└──────────────────────────────────────────────────────────────┘
```

## 1.4 Kenapa DuckLake, Bukan File `.duckdb` Biasa

DuckLake = extension DuckDB yang memisahkan **metadata** (disimpan di
Postgres, database `tabular_catalog`) dari **data fisik** (Parquet file di
MinIO/S3, bucket `tabular`). Ini yang bikin beberapa proses berbeda (SQLMesh
saat `plan`/`run`, gold-server, dan tool ad-hoc seperti
`lakehouse-setup/`) bisa semua baca/tulis ke lakehouse yang sama tanpa harus
berbagi satu file `.duckdb` lokal (yang cuma bisa dipegang 1 proses dalam
satu waktu). Konfigurasi koneksinya ada di `config.yaml`
(`gateways.duckdb.connection.catalogs.lakehouse`) dan direplikasi manual
(bukan di-share via import) di `serving/serve.py` karena gold-server sengaja
tidak bergantung pada SQLMesh runtime.

## 1.5 Kenapa "quack" (Bukan Expose Port Postgres/DuckDB Langsung)

Ada 2 titik di arsitektur ini yang pakai protokol `quack` (remote DuckDB
session lewat jaringan, extension `quack`):

1. **Bronze-bridge → model bronze** (`clinic-satusehat` → repo ini): supaya SQLMesh
   di repo ini tidak perlu kredensial MariaDB sama sekali — cukup 1 token
   (`QUACK_SOURCE_TOKEN`) yang scope-nya read-only & terbatas ke tabel
   whitelist di sisi bridge.
2. **Gold-server → dashboard backend** (`/serving/` → `/app/`): supaya
   dashboard backend tidak perlu kredensial Postgres+MinIO (DuckLake) sama
   sekali — cukup 1 token (`QUACK_SERVING_TOKEN`) yang scope-nya read-only &
   terbatas ke tabel whitelist schema `gold`.

Pola yang sama dipakai 2 kali dengan alasan yang sama: **defense in depth**
— tiap layer cuma punya akses paling minimal yang dia butuhkan, bukan
kredensial "penuh" ke lapisan storage di bawahnya.

## 1.6 Isi Tiap Bagian Repo

| Path | Isi |
|---|---|
| `config.yaml` | Konfigurasi SQLMesh: koneksi DuckLake, state DB, linter rules |
| `models/frappe/bronze/` | Model bronze — 1:1 mapping raw dari MariaDB (lewat bronze-bridge) |
| `models/frappe/silver/` | Model silver — dibersihkan, termasuk hasil flatten FHIR (`send_to_satusehat/`) |
| `models/frappe/gold/audit/` | Model gold audit compliance — lihat dokumen 03 |
| `models/satusehat/icd/` | Model referensi terminologi ICD (ICD-10, ICD-9-CM, dst) dari `seeds/icd/*.csv` |
| `seeds/audit/rule_registry.csv` | Sumber kebenaran daftar rule compliance (dibaca `gold.audit_rule`) |
| `macros/quack_bridge.py` | Macro SQLMesh `@quack_token()` — ambil token bronze-bridge dari `.env` |
| `lakehouse-setup/` | Tool CLI sekali-pakai untuk provisioning awal (bucket MinIO, database Postgres) |
| `checks/` | Script ad-hoc (**bukan** model SQLMesh) untuk eksplorasi/debug — lihat catatan penamaan di dokumen 06 |
| `serving/` | Gold-server — lihat dokumen 04 |
| `app/` | Dashboard (backend + frontend) — lihat dokumen 05 |
| `docker-compose.yaml` (root) | Infra dasar: Postgres (`metadata-catalog`) + MinIO (`object-storage`) |
| `.env` (root) | Konfigurasi & kredensial bersama — lihat dokumen 07 |
