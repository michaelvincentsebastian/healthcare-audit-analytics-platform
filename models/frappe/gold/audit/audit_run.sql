MODEL (
  name gold.audit_run,
  kind FULL,
  grain (audit_run_id)
);

-- Audit Run -- satu baris merepresentasikan kondisi compliance TERKINI, diturunkan dari
-- gold.audit_finding + watermark data silver yang dievaluasi.
--
-- STATUS PHASE 5: WIRED (Opsi A -- lihat PHASE5_REPORT.md untuk analisis lengkap & trade-off).
--
-- KENAPA BUKAN "satu run_id yang di-generate sekali lalu dipakai bersama semua check model" (ide
-- awal di komentar Phase 2): macro waktu eksekusi SQLMesh (@execution_ts, @start_ds, @end_ds, dkk)
-- HANYA resolve untuk model kind INCREMENTAL. Semua check model & audit_run di sini kind FULL, dan
-- audit_finding kind VIEW -- macro itu tidak reliable dipakai di kind-kind ini (bisa resolve ke
-- epoch 1970-01-01, bukan waktu eksekusi sesungguhnya). Lihat dokumentasi SQLMesh, macro variables.
--
-- MEKANISME PENGGANTI: audit_run_id DITURUNKAN secara deterministik dari data yang dievaluasi
-- (data_snapshot = watermark MAX(modified) gabungan seluruh tabel silver yang dipakai check) dan
-- rule_set_version (MAX(version) rule ACTIVE di gold.audit_rule) -- BUKAN dari timestamp eksekusi
-- SQLMesh. Konsekuensinya:
--   * Reproducible by construction: re-run dengan data & rule set yang sama -> audit_run_id sama.
--   * audit_run_id BERUBAH kalau data silver berubah (ada row baru/ter-modifikasi) ATAU rule set
--     berubah (rule baru/versi naik) -- bukan berubah tiap kali `sqlmesh run` diklik.
--   * audit_run MEREPRESENTASIKAN "kondisi compliance saat ini", BUKAN log historis tiap eksekusi
--     suite -- karena audit_finding kind VIEW (always-live), tidak ada momen build fisik yang bisa
--     dicatat presisi per eksekusi. Kalau ke depan dibutuhkan log historis run-per-run, itu berarti
--     mengubah audit_finding jadi kind FULL (Opsi B di PHASE5_REPORT.md) -- di luar scope Phase 5.
--
-- records_scanned: APPROKSIMASI. Total baris di 5 tabel silver yang dipakai check (tabPatient,
-- condition/observation/procedure/encounter_fhir_resource) -- BUKAN replikasi persis WHERE-clause
-- applicability tiap check (itu akan rawan drift kalau salah satu check di-update tapi hitungan
-- applicability-nya lupa disinkron). Keputusan eksplisit dikonfirmasi pemilik project.
--
-- status: SELALU 'SUCCESS' di desain ini -- karena audit_run cuma dihitung kalau query ini
-- berhasil jalan (kalau salah satu check model gagal, dependency SQLMesh akan membuat model ini
-- ikut gagal/skip, bukan menghasilkan baris dengan status FAILED/PARTIAL). Kolom status/RUNNING/
-- FAILED/PARTIAL disiapkan untuk kalau nanti orchestration-nya diubah jadi mekanisme yang bisa
-- menangkap kegagalan partial check secara eksplisit -- di luar scope Phase 5.

WITH silver_watermark AS (
  SELECT MAX(modified) AS max_modified
  FROM (
    SELECT modified FROM silver.tabPatient
    UNION ALL
    SELECT modified FROM silver.condition_fhir_resource
    UNION ALL
    SELECT modified FROM silver.observation_fhir_resource
    UNION ALL
    SELECT modified FROM silver.procedure_fhir_resource
    UNION ALL
    SELECT modified FROM silver.encounter_fhir_resource
  )
),

records_scanned AS (
  SELECT
    (SELECT COUNT(*) FROM silver.tabPatient)
    + (SELECT COUNT(*) FROM silver.condition_fhir_resource)
    + (SELECT COUNT(*) FROM silver.observation_fhir_resource)
    + (SELECT COUNT(*) FROM silver.procedure_fhir_resource)
    + (SELECT COUNT(*) FROM silver.encounter_fhir_resource) AS total
),

rule_set AS (
  SELECT MAX(version) AS rule_set_version
  FROM gold.audit_rule
  WHERE status = 'ACTIVE'
),

findings AS (
  SELECT
    COUNT(*)         AS findings_created,
    MIN(detected_at) AS earliest_detected_at,
    MAX(detected_at) AS latest_detected_at
  FROM gold.audit_finding
)

SELECT
  md5(
    COALESCE(CAST(w.max_modified AS VARCHAR), 'NA')
    || '|' || COALESCE(CAST(r.rule_set_version AS VARCHAR), 'NA')
  )                                                    AS audit_run_id,
  COALESCE(CAST(f.earliest_detected_at AS TIMESTAMP), current_timestamp) AS started_at,
  COALESCE(CAST(f.latest_detected_at AS TIMESTAMP), current_timestamp)   AS finished_at,
  CAST(r.rule_set_version AS VARCHAR)                 AS rule_set_version,
  CAST(w.max_modified AS VARCHAR)                     AS data_snapshot,
  'SUCCESS'                                            AS status,
  s.total                                              AS records_scanned,
  f.findings_created                                   AS findings_created
FROM silver_watermark w
CROSS JOIN records_scanned s
CROSS JOIN rule_set r
CROSS JOIN findings f
