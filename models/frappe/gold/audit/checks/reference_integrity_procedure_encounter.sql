MODEL (
  name gold.audit_check_reference_integrity_procedure_encounter,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-REF-PROC-ENC-001 | rule_basis: SATUSEHAT_INTEROPERABILITY
-- Authority: RuleNumber 10124 "Reference is mandatory" (lihat catatan lengkap di
-- reference_integrity_condition_encounter.sql -- pola identik, source beda).
--
-- patient_id memakai patient_ihs, sama alasan seperti terminology_icd9cm_validity.sql.

SELECT
  md5('NA' || '|CTL-REF-PROC-ENC-001|Procedure|' || p.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-REF-PROC-ENC-001'                      AS rule_id,
  1                                            AS rule_version,
  'Clinical Reference Integrity'              AS audit_domain,
  'Reference Integrity - Procedure to Encounter' AS focus_area,
  'Procedure'                                  AS entity_type,
  p.frappe_doc_name                            AS entity_id,
  p.patient_ihs                                AS patient_id,
  p.satusehat_encounter_id                     AS encounter_id,
  p.satusehat_encounter_id                     AS actual_value,
  'Encounter dengan satusehat_id tersebut harus ada di silver.encounter_fhir_resource' AS expected_value,
  'HIGH'                                       AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  p.frappe_doc_name                            AS source_record_id,
  'silver.procedure_fhir_resource:frappe_doc_name=' || p.frappe_doc_name AS evidence_reference,
  'Procedure mereferensikan Encounter (satusehat_encounter_id = ''' || p.satusehat_encounter_id || ''') yang tidak ditemukan di silver.encounter_fhir_resource' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.procedure_fhir_resource p
LEFT JOIN silver.encounter_fhir_resource e ON p.satusehat_encounter_id = e.satusehat_id
WHERE p.satusehat_encounter_id IS NOT NULL
  AND TRIM(p.satusehat_encounter_id) != ''
  AND e.satusehat_id IS NULL
