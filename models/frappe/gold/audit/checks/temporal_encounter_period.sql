MODEL (
  name gold.audit_check_temporal_encounter_period,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-TEMPORAL-ENC-001 | rule_basis: DATA_QUALITY_CONTROL
-- Tidak ada basis regulasi/SatuSehat eksplisit untuk rule ini -- murni konsistensi logis
-- internal (timeline yang mustahil bikin analitik downstream tidak reliable). Karena itu
-- rule_basis TETAP DATA_QUALITY_CONTROL, bukan SATUSEHAT_INTEROPERABILITY -- jangan naikkan
-- tanpa citation baru (lihat 02_control-matrix-final.md, bagian "Dropped" untuk kontras dengan
-- CTL-TEMPORAL-FORMAT-001 yang sengaja TIDAK diimplementasikan karena alasan applicability serupa).
--
-- Applicability: hanya Encounter yang punya period_start DAN period_end SAMA-SAMA terisi.
-- Encounter yang masih berjalan (period_end NULL, kunjungan belum selesai) BUKAN finding -- itu
-- kondisi normal, bukan pelanggaran. Di sample data yang tersedia saat implementasi, seluruh
-- Encounter punya period_end kosong (belum ada yang "selesai" tercatat) -- rule ini baru akan
-- mulai applicable begitu ada Encounter yang sudah discharge/selesai dengan period_end terisi.

SELECT
  md5('NA' || '|CTL-TEMPORAL-ENC-001|Encounter|' || e.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-TEMPORAL-ENC-001'                      AS rule_id,
  1                                            AS rule_version,
  'Data Format & Temporal Integrity'          AS audit_domain,
  'Temporal Consistency - Encounter'          AS focus_area,
  'Encounter'                                  AS entity_type,
  e.frappe_doc_name                            AS entity_id,
  e.patient                                    AS patient_id,
  e.satusehat_id                               AS encounter_id,
  CAST(e.period_start AS VARCHAR) || ' > ' || CAST(e.period_end AS VARCHAR) AS actual_value,
  'period_start <= period_end'                AS expected_value,
  'MEDIUM'                                     AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  e.frappe_doc_name                            AS source_record_id,
  'silver.encounter_fhir_resource:frappe_doc_name=' || e.frappe_doc_name AS evidence_reference,
  'Encounter.period_start (' || CAST(e.period_start AS VARCHAR) || ') lebih besar dari period_end (' || CAST(e.period_end AS VARCHAR) || ') -- timeline tidak mungkin' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.encounter_fhir_resource e
WHERE e.period_start IS NOT NULL
  AND e.period_end IS NOT NULL
  AND e.period_start > e.period_end
