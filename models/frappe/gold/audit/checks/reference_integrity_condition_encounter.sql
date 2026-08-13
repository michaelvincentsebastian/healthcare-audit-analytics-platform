MODEL (
  name gold.audit_check_reference_integrity_condition_encounter,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-REF-COND-ENC-001 | rule_basis: SATUSEHAT_INTEROPERABILITY
-- Authority: https://satusehat.kemkes.go.id/platform/docs/id/api-catalogue/validasi/list-response/
--            (RuleNumber 10124 "Reference is mandatory")
--
-- Applicability: hanya Condition yang punya satusehat_encounter_id terisi (artinya condition ini
-- memang dimaksudkan untuk link ke sebuah Encounter yang sudah/akan disubmit). Join key memakai
-- satusehat_encounter_id (sisi SatuSehat), BUKAN encounter_ref/fhir_id -- fhir_id sering kosong
-- sebelum submission sukses, dan encounter_ref adalah reference-string mentah yang belum tentu
-- konsisten formatnya. Keputusan ini sudah didokumentasikan di 02_control-matrix-final.md.

SELECT
  md5('NA' || '|CTL-REF-COND-ENC-001|Condition|' || c.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-REF-COND-ENC-001'                      AS rule_id,
  1                                            AS rule_version,
  'Clinical Reference Integrity'              AS audit_domain,
  'Reference Integrity - Condition to Encounter' AS focus_area,
  'Condition'                                  AS entity_type,
  c.frappe_doc_name                            AS entity_id,
  c.patient                                    AS patient_id,
  c.satusehat_encounter_id                     AS encounter_id,
  c.satusehat_encounter_id                     AS actual_value,
  'Encounter dengan satusehat_id tersebut harus ada di silver.encounter_fhir_resource' AS expected_value,
  'HIGH'                                       AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  c.frappe_doc_name                            AS source_record_id,
  'silver.condition_fhir_resource:frappe_doc_name=' || c.frappe_doc_name AS evidence_reference,
  'Condition mereferensikan Encounter (satusehat_encounter_id = ''' || c.satusehat_encounter_id || ''') yang tidak ditemukan di silver.encounter_fhir_resource' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.condition_fhir_resource c
LEFT JOIN silver.encounter_fhir_resource e ON c.satusehat_encounter_id = e.satusehat_id
WHERE c.satusehat_encounter_id IS NOT NULL
  AND TRIM(c.satusehat_encounter_id) != ''
  AND e.satusehat_id IS NULL
