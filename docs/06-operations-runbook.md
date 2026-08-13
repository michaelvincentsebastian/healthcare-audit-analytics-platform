# 6. Operations Runbook

## 6.1 Urutan Start (Wajib Urutan Ini)

```bash
# 1. Infra dasar
docker compose up -d                          # dari root
docker compose ps                              # tunggu object-storage healthy

# 2. Bronze-bridge (clinic-satusehat, terpisah) -- HANYA kalau mau refresh bronze
#    Cek reachability dari sini:
python3 -c "
import duckdb
c = duckdb.connect(); c.execute('INSTALL quack; LOAD quack;')
c.execute(\"ATTACH 'quack:localhost:9494' AS t (TYPE quack, TOKEN '<QUACK_SOURCE_TOKEN>', DISABLE_SSL true)\")
print(c.execute('SHOW ALL TABLES').fetchall())
"

# 3. SQLMesh
sqlmesh plan     # atau: sqlmesh plan dev  (kalau kerja di environment non-prod)
sqlmesh run

# 4. Gold-server
cd serving && docker compose up -d --build
docker compose logs -f gold-server   # tunggu "Ringkasan: N/N tabel gold ... ter-expose"

# 5. Dashboard
cd ../app && docker compose up -d --build
curl http://localhost:8000/health
```

## 6.2 Urutan Stop

Kebalikan dari start — dashboard dulu, baru gold-server, baru infra dasar
(supaya tidak ada container yang restart-loop mencoba reconnect ke sesuatu
yang sudah mati):
```bash
cd app && docker compose down
cd ../serving && docker compose down
cd .. && docker compose down   # infra dasar, HATI-HATI: ini stop Postgres+MinIO
```

## 6.3 Insiden yang Pernah Terjadi & Cara Fix

### 6.3.1 Port conflict: `Bind for 127.0.0.1:9494 failed: port is already allocated`

**Gejala**: `docker compose up -d --build` di `serving/` gagal start
`gold-server` dengan error bind port.

**Root cause yang SEBENARNYA terjadi** (bukan sekadar "2 service rebutan
port"): Docker Compose punya 2 mekanisme env yang beda —
1. `env_file: ../.env` di service → hanya inject variable ke **proses di
   dalam container**.
2. `${VAR}` di YAML (mis. di `ports:`) → di-resolve oleh **Compose CLI
   sendiri, sebelum container jalan**, dan itu cuma baca file bernama
   persis `.env` di **direktori yang sama dengan `docker-compose.yaml`**.

Kalau `serving/.env` (atau `app/.env`) tidak ada (cuma root `.env`),
`${QUACK_SERVER_HOST_PORT}` gagal ke-resolve → fallback ke default `9494`
→ bentrok dengan proses lain yang sudah pegang port itu di host (mis.
bronze-bridge kalau jalan di mesin yang sama).

**Fix**: symlink `.env` di tiap sub-folder compose ke root (lihat dokumen
02 §2.4):
```bash
cd serving && ln -s ../.env .env
cd ../app && ln -s ../.env .env
```

**Cara diagnosis kalau ini terjadi lagi**:
```bash
sudo ss -ltnp | grep 9494          # proses apa yang pegang port di OS
docker ps | grep 9494               # container mana (kalau proxy-nya docker-proxy)
```
Kalau hasilnya `docker-proxy`, itu bukan proses `serve.py` langsung — cari
`docker ps` untuk tahu **container** mana yang jadi pemiliknya. Bisa jadi
(a) bronze-bridge yang memang jalan di mesin yang sama (perilaku yang
diharapkan, tinggal pastikan port host-nya beda), atau (b) sisa container
`gold-server` versi lama dari percobaan gagal sebelumnya (`docker rm` dulu).

### 6.3.2 `sqlmesh plan`/`run` gagal di model bronze

**Gejala**: error koneksi ke `quack:localhost:9494` (atau host lain) saat
build model `bronze.*`.

**Root cause**: bronze-bridge (di `clinic-satusehat`) belum jalan atau tidak
reachable dari mesin ini. Ini **bukan** bug di repo `lakehouse` — cek status
bronze-bridge di `clinic-satusehat` dulu.

### 6.3.3 Gold-server log: "N/N tabel gold ... tapi tidak penuh" / dashboard angka 0

**Kemungkinan 1**: model gold terkait belum pernah `sqlmesh plan`/`run` di
environment yang sedang dibaca gold-server. Cek `GOLD_ENV_SUFFIX` di `.env`
(dokumen 04 §4.5) — kalau `sqlmesh plan` dijalankan tanpa environment
(`prod`, schema `gold`) tapi `GOLD_ENV_SUFFIX=__dev`, gold-server sedang baca
schema `gold__dev` yang mungkin kosong/belum ada.

**Kemungkinan 2**: rule `CTL-IDENT-PAT-COMPLETE-001` — ini **memang**
sengaja tidak pernah punya check model (`BLOCKED`, lihat dokumen 03 §3.6),
bukan bug.

**Cara verifikasi cepat**: `docker compose logs gold-server` — baris log
`build_connection()` selalu eksplisit menyebutkan tabel mana yang di-skip
dan kenapa.

### 6.3.4 Dashboard restart-loop terus

**Root cause paling umum**: gold-server belum `up`/belum sehat saat
`dashboard` start (lihat dokumen 05 §5.3, `lifespan()` fail-fast by design).

**Fix**: pastikan urutan start di §6.1 diikuti — `serving/` sebelum `app/`.
Cek `docker compose logs gold-server` (harus healthy) sebelum start
`app/`.

### 6.3.5 Error `Multiple streaming scans ... not currently supported`

Lihat dokumen 05 §5.6 untuk penjelasan lengkap. **Fix sudah ada di kode**
(`SET threads TO 1` di `lifespan()`) — kalau error ini muncul lagi, artinya
ada tempat lain yang buka koneksi baru ke `remote.*` tanpa `SET threads TO
1`, bukan masalah di query itu sendiri.

## 6.4 Cara Menambah Rule Compliance Baru

1. Tambah 1 baris di `seeds/audit/rule_registry.csv` — isi semua kolom
   (lihat kontrak di dokumen 03 §3.2), `rule_expression` = path ke file
   check model yang **akan** dibuat, `status = ACTIVE` (atau `BLOCKED` kalau
   belum siap implementasi).
2. Buat file baru di `models/frappe/gold/audit/checks/<nama>.sql`. Kontrak
   kolom **wajib PERSIS 23 kolom** yang sama seperti check lain (lihat
   dokumen 03 §3.3) — copy salah satu check existing (mis.
   `temporal_encounter_period.sql`) sebagai template, ubah logic-nya saja.
3. Tambah 1 baris `UNION ALL SELECT * FROM gold.audit_check_<nama>` di
   `models/frappe/gold/audit/audit_finding.sql`.
4. `sqlmesh plan` → review diff → `sqlmesh apply` (atau `sqlmesh run` sesuai
   workflow yang dipakai).
5. Tambah nama tabel baru (`audit_check_<nama>`) ke `GOLD_TABLES` di
   `serving/serve.py` (atau env var `GOLD_TABLES` di `.env`, lihat dokumen
   04 §4.4) — **tanpa ini, tabelnya TIDAK ke-expose ke dashboard** walau
   sudah ada datanya di DuckLake.
6. `docker compose restart gold-server` (di `serving/`) — cek log
   "Ringkasan" untuk konfirmasi tabel baru ter-expose.
7. Dashboard otomatis ikut menampilkan finding baru (query `ACTION_REGISTRY`
   sudah generic terhadap `gold.audit_finding`, tidak perlu ubah backend)
   **kecuali** Anda menambah kolom baru di luar 23 kolom kontrak — itu butuh
   perubahan di `ACTION_REGISTRY` juga.

## 6.5 Catatan: Penamaan File di `checks/` (Root) vs `models/.../checks/`

Ada 2 folder bernama `checks` dengan isi & tujuan **berbeda total** — jangan
tertukar:
- `checks/` (root repo) — script Python **ad-hoc**, bukan bagian pipeline
  SQLMesh, dipakai untuk eksplorasi/debug manual (mis.
  `checks/source_table_schema/describe.py` untuk introspeksi skema tabel
  bridge, `checks/database.py`/`checks/payload.py` untuk test koneksi
  manual). Tidak dijalankan otomatis oleh apa pun.
- `models/frappe/gold/audit/checks/` — model SQLMesh **sungguhan** (kind
  `FULL`), ini yang dimaksud "check model" di seluruh dokumen ini dan yang
  benar-benar menghasilkan data di `gold.audit_finding`.

## 6.6 Kontak/Eskalasi Antar-Repo

Kalau masalah ternyata ada di sisi bronze-bridge (`clinic-satusehat`, lihat §6.3.2),
itu di luar kewenangan perbaikan dari repo ini — koordinasikan dengan
pemegang `clinic-satusehat`. Jangan coba "perbaiki" dengan menduplikasi logic
bridge ke repo ini (sudah pernah jadi kesalahan sebelumnya — lihat riwayat
percakapan implementasi gold-server).
