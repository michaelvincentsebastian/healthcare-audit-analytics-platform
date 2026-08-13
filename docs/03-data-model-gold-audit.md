# 3. Data Model — `gold.audit_*`

Ini kontrak data yang paling penting di seluruh project — dipakai gold-server
(dokumen 04), dashboard backend (dokumen 05), dan jadi acuan kalau mau nambah
rule compliance baru (dokumen 06).

## 3.1 Diagram Relasi

```
gold.audit_rule (1) ──────< (N) gold.audit_finding
     rule_id                      rule_id (FK, bukan FK fisik -- LEFT JOIN)

gold.audit_run
     (tidak ada FK fisik ke audit_finding -- lihat §3.4, audit_run_id
      di audit_finding masih NULL by design)
```

## 3.2 `gold.audit_rule` — Rule Registry

**Sumber**: `models/frappe/gold/audit/audit_rule.sql`, `FULL` refresh dari
`seeds/audit/rule_registry.csv` (bukan SQLMesh `kind SEED` — pola CSV +
`read_csv` dipilih untuk konsisten dengan model referensi ICD di
`models/satusehat/icd/`).

**Prinsip desain**: single source of truth untuk SEMUA rule compliance.
Tidak boleh ada rule yang di-hardcode di check model tanpa row di sini
lebih dulu. `rule_expression` adalah **pointer** (path relatif ke file
check model), bukan SQL yang di-embed — logic asli tetap hidup satu tempat
saja di `models/frappe/gold/audit/checks/*.sql`.

| Kolom | Tipe | Keterangan |
|---|---|---|
| `rule_id` | VARCHAR | PK. Konvensi: `CTL-<KATEGORI>-<ENTITAS>-<NNN>`, mis. `CTL-TERM-ICD10-001` |
| `rule_name` | VARCHAR | Nama singkat rule |
| `description` | VARCHAR | Deskripsi lengkap kondisi yang dicek |
| `audit_domain` | VARCHAR | Domain besar, mis. `Clinical Terminology Compliance` |
| `focus_area` | VARCHAR | Sub-area di dalam domain |
| `rule_basis` | VARCHAR | `SATUSEHAT_INTEROPERABILITY` (berbasis dokumentasi/validasi resmi SatuSehat) atau `DATA_QUALITY_CONTROL` (konsistensi logis internal, tanpa basis regulasi eksplisit) |
| `authority_name` | VARCHAR, nullable | Sumber otoritas (mis. nama dokumen SatuSehat) |
| `authority_reference` | VARCHAR, nullable | URL/referensi ke sumber otoritas |
| `standard_name` | VARCHAR, nullable | Nama standar terminologi, mis. `ICD-10` |
| `standard_version` | VARCHAR, nullable | Versi standar, mis. `2010` — **di-CAST eksplisit ke VARCHAR** di model (lihat catatan di §3.5) |
| `rule_expression` | VARCHAR | Path relatif ke file check model yang mengimplementasikan rule ini |
| `severity` | VARCHAR | `HIGH` / `MEDIUM` / `LOW` |
| `effective_from` | DATE | Tanggal rule mulai berlaku |
| `effective_to` | DATE, nullable | Tanggal rule berhenti berlaku (NULL = masih berlaku) |
| `status` | VARCHAR | `ACTIVE` (punya check model yang jalan) atau `BLOCKED` (tercatat untuk provenance, TIDAK ada check model aktif — lihat §3.6) |
| `version` | INTEGER | Versi rule (dipakai `gold.audit_run.rule_set_version`, lihat §3.4) |
| `created_at` / `updated_at` | TIMESTAMP | Metadata registry |

## 3.3 `gold.audit_finding` — Model Sentral

**Sumber**: `models/frappe/gold/audit/audit_finding.sql`, `kind VIEW`
(always-live, bukan tabel fisik) — `UNION ALL` dari 8 check model aktif.

Setiap check model **wajib** menghasilkan baris berbentuk PERSIS 23 kolom
ini (kontrak yang sama untuk semua check, supaya `UNION ALL` valid):

| Kolom | Tipe | Keterangan |
|---|---|---|
| `finding_id` | VARCHAR | PK. `md5(audit_run_id \| rule_id \| entity_type \| entity_id)` — deterministik, bukan UUID acak |
| `audit_run_id` | VARCHAR, nullable | **Selalu NULL saat ini** — lihat §3.4 |
| `rule_id` | VARCHAR | FK logis ke `gold.audit_rule.rule_id` |
| `rule_version` | INTEGER | Versi rule saat finding ini dihasilkan |
| `audit_domain` | VARCHAR | Disalin dari rule (denormalized, supaya query dashboard tidak selalu perlu JOIN) |
| `focus_area` | VARCHAR | idem |
| `entity_type` | VARCHAR | `Patient` / `Encounter` / `Condition` / `Procedure` / `Observation` |
| `entity_id` | VARCHAR | ID record yang jadi subjek finding (biasanya `frappe_doc_name`) |
| `patient_id` | VARCHAR, nullable | ID pasien terkait, kalau applicable |
| `encounter_id` | VARCHAR, nullable | ID encounter terkait (SatuSehat ID), kalau applicable |
| `actual_value` | VARCHAR | Nilai/kondisi aktual yang ditemukan (selalu di-cast VARCHAR supaya seragam lintas tipe data check) |
| `expected_value` | VARCHAR | Nilai/kondisi yang seharusnya |
| `severity` | VARCHAR | `HIGH` / `MEDIUM` / `LOW` — disalin dari rule saat finding dibuat |
| `status` | VARCHAR | `OPEN` / `UNDER_REVIEW` / `RESOLVED` — **saat ini semua check model selalu mengisi `OPEN`**; transisi status lain (review, resolve) belum ada mekanisme write-back (lihat §3.7) |
| `detected_at` | TIMESTAMP | Waktu finding ini dihasilkan/dievaluasi |
| `resolved_at` | TIMESTAMP, nullable | Waktu finding di-resolve (belum pernah terisi — lihat §3.7) |
| `source_system` | VARCHAR | Selalu `'Frappe'` di semua check saat ini |
| `source_record_id` | VARCHAR | ID record sumber (biasanya sama dengan `entity_id`) |
| `evidence_reference` | VARCHAR | Pointer ke tabel silver + kondisi filter, format `<tabel_silver>:<kolom>=<nilai>` |
| `explanation` | VARCHAR | Penjelasan manusiawi kenapa ini jadi finding |
| `reviewer_id` | VARCHAR, nullable | Belum terisi — lihat §3.7 |
| `review_note` | VARCHAR, nullable | Belum terisi |
| `resolution_code` | VARCHAR, nullable | Belum terisi |

## 3.4 `gold.audit_run` — Snapshot Kondisi Compliance Terkini

**Sumber**: `models/frappe/gold/audit/audit_run.sql`, `kind FULL`.

⚠️ **Bukan log historis per eksekusi.** Karena `gold.audit_finding` adalah
`VIEW` (always-live), tidak ada momen build fisik yang bisa dicatat presisi
per eksekusi suite. `gold.audit_run` merepresentasikan **kondisi compliance
saat ini** (1 baris = snapshot terbaru), bukan riwayat tiap kali `sqlmesh
run` diklik.

`audit_run_id` diturunkan **deterministik** dari:
```
md5( MAX(modified) gabungan 5 tabel silver yang dipakai check | MAX(version) rule ACTIVE )
```
bukan dari timestamp eksekusi SQLMesh — alasannya: macro waktu SQLMesh
(`@execution_ts`, dst) hanya reliable untuk model `kind INCREMENTAL`, sedangkan
semua model audit di sini `kind FULL`/`VIEW`. Konsekuensinya: `audit_run_id`
**sama** kalau data & rule set sama persis (reproducible by construction),
dan **berubah** kalau ada data silver baru/berubah ATAU rule set berubah —
bukan berubah tiap klik `sqlmesh run`.

| Kolom | Tipe | Keterangan |
|---|---|---|
| `audit_run_id` | VARCHAR | PK, deterministik (lihat di atas) |
| `started_at` | TIMESTAMP | `MIN(detected_at)` dari seluruh finding saat ini |
| `finished_at` | TIMESTAMP | `MAX(detected_at)` dari seluruh finding saat ini |
| `rule_set_version` | VARCHAR | `MAX(version)` rule berstatus `ACTIVE` di `gold.audit_rule` |
| `data_snapshot` | VARCHAR | Watermark: `MAX(modified)` gabungan 5 tabel silver (`tabPatient`, `condition_fhir_resource`, `observation_fhir_resource`, `procedure_fhir_resource`, `encounter_fhir_resource`) |
| `status` | VARCHAR | **Selalu `'SUCCESS'`** saat ini — nilai lain (`RUNNING`/`FAILED`/`PARTIAL`) disiapkan skema-nya tapi belum ada mekanisme yang mengisinya (kalau salah satu check model gagal, dependency SQLMesh membuat model ini ikut gagal/skip, bukan menghasilkan baris berstatus gagal) |
| `records_scanned` | BIGINT | **Approksimasi**: total baris di 5 tabel silver di atas — BUKAN replikasi persis WHERE-clause applicability tiap check (keputusan eksplisit, supaya tidak drift kalau salah satu check di-update applicability-nya) |
| `findings_created` | BIGINT | `COUNT(*)` dari `gold.audit_finding` saat ini |

⚠️ **`gold.audit_finding.audit_run_id` masih selalu NULL** — belum di-wire
ke `gold.audit_run.audit_run_id`. Ini ditunda sengaja sampai keputusan
reproducibility-mechanism final (lihat komentar di `audit_finding.sql`).
**Jangan** isi `audit_run_id` dengan `current_timestamp`/UUID acak di model
check sebelum keputusan itu final — akan menghasilkan `audit_run_id` yang
beda tiap kali `VIEW` di-query, bukan sekali per snapshot.

## 3.5 Catatan Teknis: Kenapa `standard_version` Di-cast VARCHAR

DuckDB `read_csv` auto-infer kolom `standard_version` sebagai `BIGINT`
(semua nilai saat ini numerik, mis. `"2010"`). Kalau dibiarkan, `TRIM()` di
model `audit_rule.sql` akan gagal binding (`TRIM` butuh argumen VARCHAR).
Cast eksplisit `CAST(standard_version AS VARCHAR)` mencegah ini pecah lagi
kalau ada baris baru ditambahkan ke `rule_registry.csv`.

## 3.6 Daftar 9 Rule Compliance (Snapshot `rule_registry.csv`)

| Rule ID | Severity | Status | Check Model |
|---|---|---|---|
| `CTL-TERM-ICD10-001` | HIGH | ACTIVE | `terminology_icd10_validity.sql` |
| `CTL-TERM-ICD9CM-001` | HIGH | ACTIVE | `terminology_icd9cm_validity.sql` |
| `CTL-REF-COND-ENC-001` | HIGH | ACTIVE | `reference_integrity_condition_encounter.sql` |
| `CTL-REF-PROC-ENC-001` | HIGH | ACTIVE | `reference_integrity_procedure_encounter.sql` |
| `CTL-REF-OBS-ENC-001` | MEDIUM | ACTIVE | `reference_integrity_observation_encounter.sql` |
| `CTL-STRUCT-ENC-STATUS-001` | MEDIUM | ACTIVE | `structural_encounter_status.sql` |
| `CTL-TEMPORAL-ENC-001` | MEDIUM | ACTIVE | `temporal_encounter_period.sql` |
| `CTL-IDENT-PAT-FORMAT-001` | LOW | ACTIVE | `identity_patient_uid_format.sql` |
| `CTL-IDENT-PAT-COMPLETE-001` | MEDIUM | **BLOCKED** | *(belum diimplementasikan)* |

**`CTL-IDENT-PAT-COMPLETE-001` sengaja BLOCKED**: field mandatory untuk
kelengkapan identitas pasien belum dikonfirmasi pemilik data. Row-nya
tercatat di `gold.audit_rule` untuk provenance (supaya auditor tahu rule
ini "diketahui tapi belum jalan"), tapi **tidak ada** check model yang
berjalan untuknya, dan **tidak** muncul di `UNION ALL` `audit_finding.sql`.
Jangan implementasikan check ini sampai ada keputusan eksplisit soal field
list-nya.

**Contoh detail 1 rule** (`CTL-TEMPORAL-ENC-001`, dari
`checks/temporal_encounter_period.sql`): flag Encounter yang punya
`period_start` **dan** `period_end` sama-sama terisi tapi `period_start >
period_end` (timeline mustahil). Encounter yang masih berjalan
(`period_end` NULL) **bukan** finding — itu kondisi normal.

## 3.7 Batasan yang Diketahui (Bukan Bug)

- **Tidak ada write-back status.** Kolom `status`, `reviewer_id`,
  `review_note`, `resolution_code`, `resolved_at` ada di kontrak kolom, tapi
  belum ada mekanisme apa pun (dashboard atau lainnya) yang bisa
  mengubahnya — semua finding permanen berstatus `OPEN` sampai ada fitur
  write-back dikembangkan. Ini konsisten dengan gold-server yang **read-only**
  by design (dokumen 04) — mengubah ini butuh keputusan arsitektur baru
  (endpoint tulis terpisah, di luar scope gold-server saat ini).
- **`records_scanned` approksimasi**, bukan angka presisi per rule (§3.4).
- **`audit_run_id` di `audit_finding` selalu NULL** (§3.4).
