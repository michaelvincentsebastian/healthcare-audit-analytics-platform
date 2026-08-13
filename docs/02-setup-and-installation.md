# 2. Setup & Installation

Urutan ini WAJIB diikuti sesuai nomor — tiap langkah bergantung pada langkah
sebelumnya sudah selesai & sehat.

## 2.1 Prasyarat

- Python 3.10 / 3.11 / 3.12
- Docker + Docker Compose plugin, service Docker sedang jalan
- **[`clinic-satusehat`](https://github.com/rakhaafd/clinic-satusehat)** sudah ter-install & jalan — ini app Frappe (`clinic_satusehat`) yang jadi **sumber data utama** seluruh pipeline (lihat dokumen 01 §1.2), plus bronze-bridge yang menempel di app ini. Instalasi standar Frappe app lewat `bench` (dari dalam bench site clinic tsb, **bukan** di repo `lakehouse` ini):
  ```bash
  cd $PATH_TO_YOUR_BENCH
  bench get-app https://github.com/rakhaafd/clinic-satusehat --branch develop
  bench install-app clinic_satusehat
  ```
  ⚠️ Repo `clinic-satusehat` di luar scope dokumentasi ini — untuk detail bronze-bridge di dalamnya (lokasi script, cara jalankannya), rujuk ke repo tsb langsung atau ke pemegangnya. Kalau Anda hanya kerja di repo `lakehouse` ini (mis. develop model gold/dashboard tanpa refresh data bronze baru), langkah bronze-bridge bisa dilewati SELAMA data bronze/silver/gold yang sudah ada di DuckLake cukup untuk kebutuhan Anda.
- `openssl` atau Python (`secrets.token_hex`) untuk generate token acak.

## 2.2 Clone & Virtual Environment

```bash
git clone <url-repo-ini> lakehouse
cd lakehouse

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -r requirements.txt
```

## 2.3 Siapkan `.env` (root)

Copy dari template/`.env` yang sudah ada, atau buat baru — lihat dokumen 07
untuk daftar lengkap tiap variable dan siapa yang memakainya. Poin paling
sering kelewat:

- `QUACK_SOURCE_TOKEN` **harus identik** dengan token yang dipakai
  bronze-bridge di `clinic-satusehat` (token itu di-generate/di-set di sisi sana,
  bukan di sini — tanyakan ke pemegang repo `clinic-satusehat` kalau belum punya).
- `QUACK_SERVING_TOKEN` dan `BACKEND_API_TOKEN` **harus 2 nilai yang
  berbeda** (lihat dokumen 07 §"Kesalahan yang pernah terjadi") — generate
  masing-masing dengan:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- `LAKEHOUSE_CONNECTION_NETWORK` boleh dibiarkan default
  (`lakehouse-network`) kecuali nama itu sudah dipakai container lain di
  mesin yang sama.

## 2.4 Symlink `.env` ke Sub-Folder (WAJIB, Bukan Opsional)

`docker-compose.yaml` di `serving/` dan `app/` membaca variable Postgres/
MinIO/Quack lewat 2 mekanisme berbeda: `env_file: ../.env` (untuk isi
container) DAN interpolasi `${VAR}` langsung di YAML (untuk `ports:`,
`networks:`) yang **hanya** baca file bernama persis `.env` di direktori
yang sama dengan `docker-compose.yaml` itu sendiri. Tanpa symlink ini,
`${QUACK_SERVER_HOST_PORT}` dkk akan diam-diam fallback ke default dan bisa
menyebabkan port conflict (lihat dokumen 06, insiden yang sudah pernah
terjadi).

```bash
cd serving && ln -s ../.env .env && cd ..
cd app     && ln -s ../.env .env && cd ..
```

Verifikasi symlink benar:
```bash
ls -la serving/.env app/.env
# harus muncul "-> ../.env" di outputnya
```

## 2.5 Infra Dasar: Postgres + MinIO

```bash
docker compose up -d
docker compose ps
```

Tunggu sampai `object-storage` (MinIO) berstatus `healthy` (ada
`healthcheck` di `docker-compose.yaml`) — `metadata-catalog` (Postgres)
tidak punya healthcheck eksplisit, tapi biasanya siap dalam beberapa detik.

## 2.6 Provisioning Lakehouse (Bucket MinIO + Database Postgres)

```bash
cd lakehouse-setup
python3 main.py
# pilih "8. RUN FULL INITIAL SETUP" untuk setup awal dari nol
```

Menu ini idempotent secara terbatas — untuk kondisi rusak/sebagian
(mis. constraint Postgres bentrok), pakai pilihan "REBUILD" (3, 5, 7) alih-alih
ulangi "8" begitu saja. Lihat `lakehouse-setup/lakehouse_manager/*.py` untuk
detail tiap langkah (`storage.py` = MinIO, `pg_admin.py` = Postgres,
`catalog.py` = schema unstructured).

## 2.7 SQLMesh: Init & Plan Pertama Kali

Kalau `.sqlmesh/` (state lokal) belum pernah di-init:
```bash
sqlmesh init
# 1. What type of project? -> 3
# 2. Choose SQL engine?    -> 1
# 3. CLI experience?       -> 1
```

Jalankan plan (memastikan bronze-bridge di `clinic-satusehat` SUDAH hidup &
reachable sebelum langkah ini, kalau Anda butuh refresh bronze):
```bash
sqlmesh plan
```

⚠️ **Kalau bronze-bridge belum jalan**, `sqlmesh plan` akan gagal di model
`bronze.*` dengan error koneksi ke `quack:localhost:9494` (atau host lain
sesuai `QUACK_URI`) — ini bukan bug di repo ini, cek dulu status bronze-bridge
di sisi `clinic-satusehat`.

Model gold (`gold.audit_*`) baru punya data setelah model silver yang jadi
dependensinya (`silver.tabPatient`, `silver.condition_fhir_resource`, dst)
sudah punya data.

## 2.8 Gold-Server (`/serving/`)

```bash
cd serving
docker compose up -d --build
docker compose logs -f gold-server
```

Cek log: harus ada baris `Ringkasan: N/N tabel gold (dari whitelist)
ter-expose`. Kalau `N/N` tidak penuh (ada tabel whitelist yang belum ada di
catalog), itu **normal** kalau `sqlmesh plan` di langkah 2.7 belum
menjangkau semua model gold — lihat dokumen 04 untuk detail whitelist.

Detail lengkap arsitektur & troubleshooting gold-server ada di dokumen 04.

## 2.9 Dashboard (`/app/`)

**Urutan penting**: gold-server (2.8) harus sudah `up` & sehat dulu sebelum
langkah ini — `app/backend/main.py` fail-fast (restart-loop) kalau gold-server
belum bisa dikontak saat startup.

```bash
cd app
docker compose up -d --build
```

Buka `http://localhost:8000` (atau `DASHBOARD_HOST_PORT` kalau di-override).

Detail lengkap ada di dokumen 05.

## 2.10 Checklist Verifikasi Akhir

- [ ] `docker compose ps` (root) → `metadata-catalog` & `object-storage` running
- [ ] `docker compose ps` (di `serving/`) → `gold-server` **healthy**
- [ ] `docker compose ps` (di `app/`) → `dashboard` **running** (bukan restarting)
- [ ] `curl http://localhost:8000/health` → `{"status":"ok","quack_connected":true,"gold_reachable":true}`
- [ ] Buka dashboard di browser → angka di overview **tidak error** (boleh 0 kalau `sqlmesh run` belum pernah sampai gold, itu bukan error)

## 2.11 Alur Ingest FHIR (Ringkas)

Ini alur khusus untuk data SatuSehat FHIR (bukan bagian dari urutan startup
di atas — dilakukan setiap ada resource FHIR baru/berubah). Detail penuh ada
di `README.md` root, ringkasannya:

1. Extract `payload_json` dari tiap endpoint FHIR SatuSehat.
2. Taruh di `flatquack/input/<resource_name>.txt`.
3. Rancang/perbarui ViewDefinition di `flatquack/views/` (kontrak flatten FHIR → tabular).
4. Jalankan flatquack → hasil query flatten di `flatquack/output/flatten_query.sql`.
5. Sesuaikan query itu ke dialek SQLMesh+DuckDB, tempel ke model silver yang sesuai (`models/frappe/silver/send_to_satusehat/`).
6. `sqlmesh plan`.

⚠️ Kalau format FHIR SatuSehat berubah, ViewDefinition **harus dirancang
ulang manual** — flatquack tidak mendeteksi perubahan format secara otomatis.
