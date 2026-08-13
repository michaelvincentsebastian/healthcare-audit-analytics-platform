MODEL (
  name gold.audit_check_terminology_icd9cm_validity,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-TERM-ICD9CM-001 | rule_basis: SATUSEHAT_INTEROPERABILITY
-- Authority: https://satusehat.kemkes.go.id/platform/docs/id/fhir/resources/procedure/
--            (contoh payload resmi eksplisit pakai system http://hl7.org/fhir/sid/icd-9-cm,
--            cocok persis dengan sample data kita: code = "87.44")
--            https://satusehat.kemkes.go.id/platform/docs/id/api-catalogue/validasi/list-response/
--            (RuleNumber 10001 "Code not found")
--
-- Applicability: hanya Procedure dengan code terisi.
--
-- patient_id memakai patient_ihs (BUKAN kolom "patient" seperti Condition/Observation) --
-- procedure_fhir_resource tidak punya kolom "patient" langsung. Lihat
-- models_dependencies/audit/README.md Section 4 untuk penjelasan asimetri ini.

SELECT
  md5('NA' || '|CTL-TERM-ICD9CM-001|Procedure|' || p.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-TERM-ICD9CM-001'                       AS rule_id,
  1                                            AS rule_version,
  'Clinical Terminology Compliance'           AS audit_domain,
  'Terminology - ICD-9-CM'                    AS focus_area,
  'Procedure'                                  AS entity_type,
  p.frappe_doc_name                            AS entity_id,
  p.patient_ihs                                AS patient_id,
  p.satusehat_encounter_id                     AS encounter_id,
  p.code                                       AS actual_value,
  'Kode harus terdaftar di bronze.icd_9cm (ICD-9-CM 2010)' AS expected_value,
  'HIGH'                                       AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  p.frappe_doc_name                            AS source_record_id,
  'silver.procedure_fhir_resource:frappe_doc_name=' || p.frappe_doc_name AS evidence_reference,
  'Procedure code ''' || p.code || ''' tidak ditemukan di bronze.icd_9cm (ICD-9-CM 2010)' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.procedure_fhir_resource p
LEFT JOIN bronze.icd_9cm r ON TRIM(p.code) = TRIM(r.code)
WHERE p.code IS NOT NULL
  AND TRIM(p.code) != ''
  AND r.code IS NULL
