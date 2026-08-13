# Dokumentasi Teknis — Healthcare Compliance Audit Lakehouse

Dokumentasi end-to-end untuk project ini: dari raw data di Frappe/MariaDB
sampai dashboard audit compliance yang dilihat user akhir. Ditulis
berdasarkan kode & konfigurasi yang benar-benar ada di repo ini (bukan
rencana/aspirasi) per commit terakhir yang didokumentasikan.

## Daftar Isi

| # | Dokumen | Isinya |
|---|---|---|
| 1 | [01-architecture-overview.md](01-architecture-overview.md) | Gambaran besar: medallion layers (bronze/silver/gold), posisi tiap repo, diagram alur data end-to-end |
| 2 | [02-setup-and-installation.md](02-setup-and-installation.md) | Cara setup dari nol: prasyarat, urutan `docker compose up`, `sqlmesh plan/run`, checklist verifikasi |
| 3 | [03-data-model-gold-audit.md](03-data-model-gold-audit.md) | Skema `gold.*`: `audit_rule`, `audit_run`, `audit_finding`, daftar 9 rule compliance & status masing-masing |
| 4 | [04-serving-layer.md](04-serving-layer.md) | Gold-server (`/serving/`) — cara kerja, konfigurasi, whitelist tabel, keamanan |
| 5 | [05-dashboard.md](05-dashboard.md) | Dashboard (`/app/`) — backend FastAPI, `ACTION_REGISTRY`, frontend, alur auth |
| 6 | [06-operations-runbook.md](06-operations-runbook.md) | Runbook: urutan start/stop, cara tambah rule baru, troubleshooting masalah yang sudah pernah terjadi |
| 7 | [07-security-and-secrets.md](07-security-and-secrets.md) | Semua token & kredensial: apa isinya, siapa yang pegang, kenapa dipisah |

## Cara Baca Cepat

- **Baru pertama kali pegang project ini?** Mulai dari `01` lalu `02`.
- **Mau nambah rule audit baru?** Langsung ke `03` (kontrak kolom) lalu `06` (langkah praktis).
- **Server/dashboard error, butuh debug cepat?** Langsung ke `06`.
- **Butuh tahu token mana yang boleh dipegang siapa?** `07`.

## Konvensi Penulisan

- Kode/perintah persis seperti yang ada di repo — bukan disederhanakan.
- Bagian yang **belum diverifikasi berjalan end-to-end** (mis. belum pernah dites lewat Docker sungguhan) ditandai eksplisit ⚠️, bukan ditulis seolah-olah sudah pasti berhasil.
- Istilah teknis yang dipakai bolak-balik Indonesia/Inggris (mis. "grain", "watermark") sengaja tidak diterjemahkan paksa — mengikuti istilah yang dipakai kode & tool aslinya (SQLMesh, DuckDB) supaya gampang di-Google kalau butuh referensi lebih lanjut.
