# 4. Serving Layer — Gold Server (`/serving/`)

## 4.1 Tanggung Jawab

Satu-satunya tanggung jawab folder ini: **ATTACH ke katalog DuckLake, expose
tabel-tabel gold yang di-whitelist sebagai view read-only, serve lewat
`quack_serve`.** Tidak ada logic bisnis, tidak ada transformasi data — itu
semua sudah selesai di layer SQLMesh (model gold). Gold-server murni "jendela
baca" ke hasil akhir yang sudah jadi.

⚠️ **Bukan tempat bronze-bridge.** Bridge MariaDB→bronze ada di repo Frappe
terpisah (lihat dokumen 01 §1.2) — tidak ada file/service untuk itu di
folder ini.

## 4.2 Isi Folder

| File | Fungsi |
|---|---|
| `serve.py` | Proses utama — lihat §4.3 |
| `healthcheck.py` | Dipanggil Docker `HEALTHCHECK`, probe `SELECT 1` lewat quack |
| `Dockerfile` | Image Python 3.12-slim, install `duckdb`+`python-dotenv`+`pytz`, `COPY serve.py healthcheck.py` |
| `docker-compose.yaml` | 1 service: `gold-server` |
| `.env` | **Symlink** ke `../.env` (root) — lihat dokumen 02 §2.4 kenapa ini wajib symlink, bukan file terpisah |
| `requirements.txt` | `duckdb==1.5.4`, `python-dotenv`, `pytz` |

## 4.3 Cara Kerja `serve.py`

Urutan startup (fungsi `build_connection()` lalu `main()`):

1. `INSTALL`/`LOAD` extension: `ducklake`, `postgres`, `httpfs`, `quack`.
2. Buat S3 secret (`minio_config`) dari `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_ENDPOINT`.
3. `ATTACH 'ducklake:postgres:...' AS lakehouse (DATA_PATH 's3://tabular/', READ_ONLY)` — connection string persis meniru `config.yaml` SQLMesh, tapi ditulis manual (gold-server tidak menjalankan SQLMesh runtime).
4. Sanity check: query `information_schema.schemata WHERE catalog_name = 'lakehouse'` — fail-fast kalau attach gagal, daripada baru ketahuan saat request pertama masuk.

   ⚠️ **Catatan teknis penting**: katalog eksternal (di-ATTACH lewat
   extension seperti `ducklake`/`postgres`) **tidak** punya
   `<catalog>.information_schema` sendiri seperti native DuckDB catalog.
   `information_schema` cuma tersedia sebagai view global tanpa prefix
   catalog, gabungan metadata SEMUA database yang ter-attach — makanya
   difilter pakai kolom `table_catalog`/`catalog_name`, bukan diakses lewat
   `lakehouse.information_schema...`.
5. `CREATE SCHEMA IF NOT EXISTS "gold"` (schema lokal, tempat view diletakkan).
6. Cek existensi tiap tabel di `GOLD_TABLES` (whitelist) terhadap `information_schema.tables` — tabel yang belum ada di-skip dengan warning (bukan error fatal), supaya server tetap bisa start walau sebagian model gold belum pernah `sqlmesh run`.
7. Untuk tiap tabel whitelist yang **ada**: `CREATE OR REPLACE VIEW "gold"."<t>" AS SELECT * FROM lakehouse."<schema>"."<t>"`, lalu `SELECT * ... LIMIT 1` untuk verifikasi view valid (LIMIT 1, bukan `count(*)` — `count(*)` di atas view attached lewat extension eksternal rawan memicu bug internal DuckDB terkait *count_star pushdown*).
8. `quack_serve('quack:<QUACK_BIND_HOST>:<QUACK_PORT>', token => QUACK_SERVING_TOKEN)`.
9. `CREATE MACRO read_only(...)` + `SET GLOBAL quack_authorization_function = 'read_only'` — regex whitelist verb SQL (`SELECT|FROM|WITH|EXPLAIN|DESCRIBE|SHOW`) di awal tiap query masuk.
10. Loop `while` yang menunggu `SIGTERM`/`SIGINT` (bukan `input()` — `input()` gagal `EOFError` di container `-d` karena stdin tertutup), heartbeat log tiap 5 menit.

## 4.4 Whitelist Tabel Gold — `GOLD_TABLES`

**Bukan** auto-discover semua isi schema `gold` — sengaja whitelist
eksplisit. Alasan: tabel baru di schema gold harus **sengaja** ditambahkan
sebelum ke-expose ke dashboard, lebih aman daripada otomatis ke-expose
begitu `sqlmesh run` sukses (mis. tabel internal/staging yang belum siap
publik).

Default (`_DEFAULT_GOLD_TABLES` di `serve.py`):
```
audit_rule, audit_finding, audit_run,
audit_check_identity_patient_uid_format,
audit_check_reference_integrity_condition_encounter,
audit_check_reference_integrity_observation_encounter,
audit_check_reference_integrity_procedure_encounter,
audit_check_structural_encounter_status,
audit_check_temporal_encounter_period,
audit_check_terminology_icd9cm_validity,
audit_check_terminology_icd10_validity
```

Bisa di-override **total** lewat env var `GOLD_TABLES` (comma-separated) —
tambah tabel gold baru ke serving tidak perlu edit source code, cukup update
`.env` lalu **restart container** (tidak ada hot-reload; lihat dokumen 06
untuk langkah lengkapnya).

## 4.5 Schema Gold & `GOLD_ENV_SUFFIX`

Nama schema gold yang dibaca ikut konvensi virtual-environment SQLMesh:
environment `prod` tidak ada suffix (schema fisiknya persis `gold`), tapi
environment lain (mis. hasil `sqlmesh plan dev`) di-suffix otomatis oleh
SQLMesh jadi `gold__dev`, `gold__staging`, dst.

```
GOLD_SCHEMA = f"{GOLD_SCHEMA_BASE}{GOLD_ENV_SUFFIX}"
```

`.env` saat ini punya `GOLD_ENV_SUFFIX=__dev` — artinya gold-server sedang
membaca schema **`gold__dev`**, bukan `gold` production. ⚠️ Kalau Anda
mengharapkan data dari `sqlmesh plan` (tanpa environment/`prod`) tapi
gold-server melapor tabel kosong/tidak ada, cek dulu nilai
`GOLD_ENV_SUFFIX` ini — penyebab paling umum salah-baca environment.

## 4.6 Konfigurasi (Environment Variables)

| Variable | Wajib? | Default | Keterangan |
|---|---|---|---|
| `POSTGRES_HOST/PORT/USER/PASSWORD` | Ya | — | Koneksi ke katalog metadata DuckLake. Di docker-compose, `POSTGRES_HOST` di-override ke `metadata-catalog` (nama container) |
| `TABULAR_METADATA_DB_NAME` | Ya | — | Nama database Postgres untuk katalog `lakehouse` |
| `MINIO_ACCESS_KEY/SECRET_KEY` | Ya | — | Kredensial S3/MinIO |
| `MINIO_ENDPOINT` | Tidak | `localhost:9000` | Di docker-compose, di-override ke `object-storage:9000` (nama container) |
| `MINIO_USE_SSL` | Tidak | `false` | — |
| `TABULAR_BUCKET` | Ya | — | Bucket data DuckLake, `s3://<bucket>/` |
| `QUACK_BIND_HOST` | Tidak | `0.0.0.0` | Host bind **di dalam container** |
| `QUACK_PORT` | Tidak | `9494` | Port **internal container** — lihat §4.7 soal ini vs `QUACK_SERVER_HOST_PORT` |
| `QUACK_SERVER_HOST_PORT` | Tidak | `9494` (di compose) | Port di **host**, dipetakan ke `QUACK_PORT` di container. **Ini yang diubah kalau mau ganti port dari luar**, bukan `QUACK_PORT` |
| `QUACK_SERVING_TOKEN` | Ya | — | Token statis untuk client (dashboard backend) autentikasi ke gold-server |
| `QUACK_ALLOW_OTHER_HOSTNAME` | Tidak | `true` | Set `false` kalau client & server pasti di mesin yang sama |
| `GOLD_SCHEMA` | Tidak | `gold` | Base nama schema (lihat §4.5) |
| `GOLD_ENV_SUFFIX` | Tidak | `""` (kode) / `__dev` (.env saat ini) | Suffix environment SQLMesh (lihat §4.5) |
| `GOLD_TABLES` | Tidak | Lihat §4.4 | Override total whitelist tabel |

## 4.7 Port: Internal vs Host

Ini sumber bug yang **sudah pernah terjadi** (lihat dokumen 06 §"Port
conflict"), jadi ditulis eksplisit di sini:

- `QUACK_PORT` = port **di dalam** container tempat `quack_serve` listen. **Jangan diubah** dari `9494` kecuali ada alasan kuat — ini bukan yang perlu diutak-atik untuk menghindari bentrok port di host.
- `QUACK_SERVER_HOST_PORT` = port yang di-mapping di **host**. **Ini** yang diubah kalau port 9494 di host sudah dipakai proses lain (mis. bronze-bridge yang kebetulan jalan di mesin yang sama). `.env` saat ini sudah set `QUACK_SERVER_HOST_PORT=9495` dan `QUACK_URI=quack:localhost:9495` supaya konsisten di sisi client.

Baris relevan di `serving/docker-compose.yaml`:
```yaml
ports:
  - "${QUACK_SERVER_HOST:-127.0.0.1}:${QUACK_SERVER_HOST_PORT:-9494}:9494"
```

## 4.8 Keamanan — 3 Lapis Read-Only

1. `ATTACH ... READ_ONLY` di level DuckLake attach — proses ini secara
   fundamental tidak bisa menulis balik ke lakehouse.
2. `quack_authorization_function = 'read_only'` — regex whitelist verb SQL
   di level query yang masuk lewat quack (`SELECT`/`FROM`/`WITH`/`EXPLAIN`/
   `DESCRIBE`/`SHOW` saja).
3. Whitelist tabel (`GOLD_TABLES`) — bahkan untuk operasi baca, cuma tabel
   yang di-whitelist eksplisit yang punya view & bisa diakses; sisanya
   (mis. tabel bronze/silver, tabel gold di luar whitelist) sama sekali
   tidak ada view-nya di sesi ini, jadi tidak bisa diquery lewat quack sama
   sekali walau attacker tahu nama tabelnya.

## 4.9 Cara Restart / Refresh Setelah Ada Model Gold Baru

Tidak ada hot-reload — whitelist & daftar view dibangun sekali saat startup.
```bash
cd serving
# kalau nambah tabel ke GOLD_TABLES di .env dulu, baru:
docker compose restart gold-server
docker compose logs -f gold-server   # cek baris "Ringkasan: N/N tabel ..."
```
