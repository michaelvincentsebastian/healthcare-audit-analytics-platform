MODEL (
  name gold.audit_run,
  kind FULL,
  grain (audit_run_id)
);

-- Audit Run -- satu baris per eksekusi audit suite (bukan per check model individual).
--
-- STATUS PHASE 2: SKELETON. Skema kolom sudah final dan boleh diintegrasikan ke serving layer
-- sekarang (Phase 6), tapi model ini akan SELALU 0 baris sampai Phase 5 (orchestration wiring)
-- selesai. Alasan belum diisi di Phase 2: reproducibility butuh SATU run_id yang sama dipakai
-- bersama oleh SEMUA check model yang jalan dalam satu eksekusi (lihat 03_data-model-specs.md),
-- dan mekanisme itu (macro/blueprint variable yang di-share ke seluruh check model + langkah yang
-- menulis baris ini setelah suite selesai jalan) baru dibangun di Phase 5, setelah check model
-- (Phase 3-4) benar-benar ada untuk dihubungkan.
--
-- PENTING -- jangan disalahartikan: 0 baris di sini BUKAN berarti "audit belum menemukan
-- masalah", tapi "audit belum pernah dieksekusi lewat mekanisme yang reproducible". Dashboard
-- (Phase 7) harus membedakan dua kondisi ini secara eksplisit -- lihat catatan yang sama di
-- audit_finding.sql.

SELECT
  CAST(NULL AS VARCHAR)    AS audit_run_id,      -- UUID atau ID deterministik berbasis timestamp
  CAST(NULL AS TIMESTAMP)  AS started_at,
  CAST(NULL AS TIMESTAMP)  AS finished_at,        -- nullable selagi masih RUNNING
  CAST(NULL AS VARCHAR)    AS rule_set_version,    -- snapshot MAX(audit_rule.version) atau hash rule aktif saat run
  CAST(NULL AS VARCHAR)    AS data_snapshot,       -- referensi snapshot DuckLake / watermark MAX(modified) yang dievaluasi
  CAST(NULL AS VARCHAR)    AS status,              -- RUNNING | SUCCESS | FAILED | PARTIAL
  CAST(NULL AS BIGINT)     AS records_scanned,
  CAST(NULL AS BIGINT)     AS findings_created
WHERE 1 = 0
