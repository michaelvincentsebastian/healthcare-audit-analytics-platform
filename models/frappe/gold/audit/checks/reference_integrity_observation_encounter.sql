MODEL (
  name gold.audit_check_reference_integrity_observation_encounter,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-REF-OBS-ENC-001 | rule_basis: SATUSEHAT_INTEROPERABILITY
-- Authority: RuleNumber 10124 "Reference is mandatory" (pola identik dengan 2 check
-- reference-integrity lainnya, source beda). Severity MEDIUM (bukan HIGH) -- bobot klinis
-- Observation lebih rendah dibanding Condition/Procedure, sesuai draft severity di
-- 02_control-matrix-final.md.

SELECT
  md5('NA' || '|CTL-REF-OBS-ENC-001|Observation|' || o.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-REF-OBS-ENC-001'                       AS rule_id,
  1                                            AS rule_version,
  'Clinical Reference Integrity'              AS audit_domain,
  'Reference Integrity - Observation to Encounter' AS focus_area,
  'Observation'                                AS entity_type,
  o.frappe_doc_name                            AS entity_id,
  o.patient                                    AS patient_id,
  o.satusehat_encounter_id                     AS encounter_id,
  o.satusehat_encounter_id                     AS actual_value,
  'Encounter dengan satusehat_id tersebut harus ada di silver.encounter_fhir_resource' AS expected_value,
  'MEDIUM'                                     AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  o.frappe_doc_name                            AS source_record_id,
  'silver.observation_fhir_resource:frappe_doc_name=' || o.frappe_doc_name AS evidence_reference,
  'Observation mereferensikan Encounter (satusehat_encounter_id = ''' || o.satusehat_encounter_id || ''') yang tidak ditemukan di silver.encounter_fhir_resource' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.observation_fhir_resource o
LEFT JOIN silver.encounter_fhir_resource e ON o.satusehat_encounter_id = e.satusehat_id
WHERE o.satusehat_encounter_id IS NOT NULL
  AND TRIM(o.satusehat_encounter_id) != ''
  AND e.satusehat_id IS NULL
