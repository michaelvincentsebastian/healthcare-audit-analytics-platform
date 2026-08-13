MODEL (
  name gold.audit_check_structural_encounter_status,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-STRUCT-ENC-STATUS-001 | rule_basis: SATUSEHAT_INTEROPERABILITY
-- Authority: https://satusehat.kemkes.go.id/platform/docs/id/fhir/resources/encounter/
--            ("3 status yang wajib dikirimkan": arrived, in-progress, finished)
--
-- Applicability: hanya Encounter dengan fhir_status terisi. Caveat yang WAJIB dibaca sebelum
-- mengubah threshold rule ini: sample data yang tersedia saat implementasi (checks/output) cuma
-- berisi status 'arrived' (sample kecil, 8 baris) -- belum ada bukti langsung fhir_status di
-- kolom silver ini pernah/tidak pernah legitimately berisi status FHIR EncounterStatus lain
-- (mis. 'planned', 'cancelled') di luar 3 status yang SatuSehat wajibkan saat submit. Kalau nanti
-- ternyata fhir_status memang bisa legitimately berisi status FHIR generik lain di titik siklus
-- tertentu (bukan cuma di titik submit), WHERE clause ini perlu dipersempit supaya tidak
-- false-positive -- lihat 02_control-matrix-final.md.

SELECT
  md5('NA' || '|CTL-STRUCT-ENC-STATUS-001|Encounter|' || e.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-STRUCT-ENC-STATUS-001'                 AS rule_id,
  1                                            AS rule_version,
  'EHR/FHIR Structural Compliance'            AS audit_domain,
  'Structural - Encounter Status'             AS focus_area,
  'Encounter'                                  AS entity_type,
  e.frappe_doc_name                            AS entity_id,
  e.patient                                    AS patient_id,
  e.satusehat_id                               AS encounter_id,
  e.fhir_status                                AS actual_value,
  'arrived | in-progress | finished'          AS expected_value,
  'MEDIUM'                                     AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  e.frappe_doc_name                            AS source_record_id,
  'silver.encounter_fhir_resource:frappe_doc_name=' || e.frappe_doc_name AS evidence_reference,
  'Encounter.status (''' || e.fhir_status || ''') bukan salah satu dari 3 status yang wajib dikirim SatuSehat: arrived, in-progress, finished' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.encounter_fhir_resource e
WHERE e.fhir_status IS NOT NULL
  AND TRIM(e.fhir_status) != ''
  AND e.fhir_status NOT IN ('arrived', 'in-progress', 'finished')
