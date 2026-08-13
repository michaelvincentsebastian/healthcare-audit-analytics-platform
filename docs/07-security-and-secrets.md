# 7. Security & Secrets

## 7.1 Peta Semua Token/Kredensial

| Variable | Dipegang oleh | Dipakai untuk | Terekspos ke browser? |
|---|---|---|---|
| `POSTGRES_PASSWORD` | Postgres container, gold-server, SQLMesh, `lakehouse-setup/` | Auth ke database metadata catalog & state SQLMesh | Tidak |
| `MINIO_SECRET_KEY` | MinIO container, gold-server, SQLMesh, `lakehouse-setup/` | Auth ke object storage | Tidak |
| `QUACK_SOURCE_TOKEN` | Bronze-bridge (repo Frappe), model bronze (`macros/quack_bridge.py`) | Client di repo ini autentikasi ke bronze-bridge | Tidak |
| `QUACK_SERVING_TOKEN` | Gold-server (`serving/serve.py`), dashboard backend (`app/backend/main.py`) | Dashboard backend autentikasi ke gold-server (server-to-server) | **Tidak — tidak pernah** |
| `BACKEND_API_TOKEN` | Dashboard backend, frontend (disuntik runtime via `/config.js`) | Browser autentikasi ke dashboard backend | **Ya, by design** (endpoint internal-only) |

## 7.2 Kenapa `QUACK_SERVING_TOKEN` dan `BACKEND_API_TOKEN` Harus Beda

Dua token ini melindungi 2 **lapisan trust yang berbeda**:

- `QUACK_SERVING_TOKEN` → server-to-server (dashboard backend ↔ gold-server),
  **tidak pernah** keluar dari infrastruktur backend, risiko exposure rendah.
- `BACKEND_API_TOKEN` → client-facing (browser ↔ dashboard backend),
  terkirim ke browser lewat `/config.js`, bisa dilihat siapa pun yang punya
  akses ke devtools/network tab di browser yang sedang buka dashboard —
  risiko exposure jauh lebih tinggi.

⚠️ **Kalau kedua nilai ini sama** dan `BACKEND_API_TOKEN` bocor dari
browser, token itu otomatis juga valid untuk query langsung ke gold-server
tanpa lewat `ACTION_REGISTRY` (bypass semua batasan query yang didefinisikan
di backend). Ini pernah terjadi di draft awal `.env` project ini (kedua
variable ke-copy-paste sama) — pastikan sudah di-generate ulang terpisah
sebelum deploy ke environment yang bisa diakses lebih dari satu orang.

Generate token baru:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 7.3 Prinsip Defense in Depth yang Dipakai di Seluruh Arsitektur

Pola yang sama diulang 2 kali secara sengaja (lihat dokumen 01 §1.5):

1. **Bronze-bridge**: MariaDB credential **tidak pernah** ada di repo ini —
   cuma 1 token read-only+whitelist (`QUACK_SOURCE_TOKEN`).
2. **Gold-server**: Postgres+MinIO credential (DuckLake) **tidak pernah**
   ada di proses dashboard backend — cuma 1 token read-only+whitelist
   (`QUACK_SERVING_TOKEN`).

Tiap layer cuma punya akses paling minimal yang dia butuhkan untuk
fungsinya sendiri, bukan kredensial "penuh" ke lapisan storage di bawahnya.
Kalau salah satu layer di-compromise, blast radius-nya terbatas ke apa yang
di-whitelist layer itu saja.

## 7.4 Read-Only Enforcement

Gold-server menegakkan read-only di **3 lapis independen** (detail teknis
di dokumen 04 §4.8):
1. `ATTACH ... READ_ONLY` (level DuckLake attach)
2. `quack_authorization_function` (regex whitelist verb SQL, level query)
3. Whitelist tabel eksplisit (`GOLD_TABLES`, level akses per-tabel)

Dashboard backend menambah 1 lapis lagi di sisi aplikasi: **tidak ada raw
SQL dari browser sama sekali** — hanya `{action, params}` yang dipetakan ke
query statis di `ACTION_REGISTRY` dengan parameter yang selalu di-bind
(`?`), tidak ada string-building SQL dari input user.

## 7.5 Jaringan (Network Isolation)

- `lakehouse-network` (docker network) menghubungkan `postgres`, `minio`,
  `gold-server`, dan `dashboard` — Postgres & MinIO **tidak** expose port ke
  host lewat network ini (koneksi antar-container pakai hostname internal:
  `metadata-catalog`, `object-storage`).
- Gold-server expose 1 port ke host (`QUACK_SERVER_HOST_PORT`, default
  `9495`) — HANYA untuk kebutuhan development/debug manual dari host
  (mis. `quack_query` ad-hoc). Kalau dashboard adalah satu-satunya
  consumer di production, port ini **bisa dihapus** dari `ports:` di
  `serving/docker-compose.yaml` supaya gold-server sama sekali tidak
  reachable dari luar docker network.
- Dashboard expose `DASHBOARD_HOST_PORT` (default `8000`) — ini **memang**
  perlu diakses dari luar (browser user), tapi harus **internal-only**
  (jaringan kantor/VPN) — lihat §7.6.

## 7.6 Batasan yang Harus Diketahui Sebelum Deploy ke Luar Jaringan Lokal

- Dashboard **tidak punya sistem login**. `BACKEND_API_TOKEN` adalah
  satu-satunya lapisan auth, dan didesain untuk skenario internal-only
  (semua orang yang boleh akses dashboard dianggap trusted).
- `CORSMiddleware` di backend di-set `allow_origins=["*"]` — cocok untuk
  internal-only, **harus diperketat** kalau dashboard di-deploy ke
  environment yang bisa diakses origin lain.
- `QUACK_DISABLE_SSL=true` di `.env` — traffic quack **tidak terenkripsi**.
  Ini oke selama traffic tidak pernah keluar jaringan lokal/docker network
  (sesuai desain saat ini). Kalau ke depan gold-server/dashboard di-deploy
  lintas mesin lewat jaringan publik, ini **harus** diaktifkan SSL-nya.

**Kesimpulan**: sebelum expose dashboard ini ke internet terbuka, minimal
tambahkan reverse proxy dengan auth tambahan (SSO/basic auth/VPN-only) di
depan container `dashboard` — jangan andalkan `BACKEND_API_TOKEN` saja
sebagai satu-satunya lapisan pertahanan.
