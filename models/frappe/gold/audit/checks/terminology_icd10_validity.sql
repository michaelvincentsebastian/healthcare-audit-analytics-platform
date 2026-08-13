MODEL (
  name gold.audit_check_terminology_icd10_validity,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-TERM-ICD10-001 | rule_basis: SATUSEHAT_INTEROPERABILITY
-- Authority: https://satusehat.kemkes.go.id/platform/docs/id/fhir/resources/condition/
--            https://satusehat.kemkes.go.id/platform/docs/id/api-catalogue/validasi/list-response/
--            (RuleNumber 10001 "Code not found")
--
-- Applicability: hanya Condition dengan icd_code terisi. icd_code kosong/NULL bukan finding --
-- baris itu belum applicable ke rule ini (mis. diagnosis belum diinput lengkap, di luar cakupan
-- audit terminology).
--
-- Field ganda: condition_fhir_resource punya icd_code (Frappe passthrough) DAN code/code_display
-- (dari FHIR payload). Rule ini pakai icd_code sebagai primary evidence (keputusan discovery --
-- lihat 02_control-matrix-final.md catatan). Kalau kedua field itu ternyata berbeda nilainya,
-- itu temuan data-quality tersendiri, TIDAK dicek di sini (di luar scope 9 kontrol MVP).
--
-- Lihat models_dependencies/audit/README.md untuk konvensi finding_id / audit_run_id / detected_at.

SELECT
  md5('NA' || '|CTL-TERM-ICD10-001|Condition|' || c.frappe_doc_name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-TERM-ICD10-001'                        AS rule_id,
  1                                            AS rule_version,
  'Clinical Terminology Compliance'           AS audit_domain,
  'Terminology - ICD-10'                      AS focus_area,
  'Condition'                                  AS entity_type,
  c.frappe_doc_name                            AS entity_id,
  c.patient                                    AS patient_id,
  c.satusehat_encounter_id                     AS encounter_id,
  c.icd_code                                   AS actual_value,
  'Kode harus terdaftar di bronze.icd_10 (ICD-10 2010)' AS expected_value,
  'HIGH'                                       AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  c.frappe_doc_name                            AS source_record_id,
  'silver.condition_fhir_resource:frappe_doc_name=' || c.frappe_doc_name AS evidence_reference,
  'Diagnosis code ''' || c.icd_code || ''' tidak ditemukan di bronze.icd_10 (ICD-10 2010)' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.condition_fhir_resource c
LEFT JOIN bronze.icd_10 r ON TRIM(c.icd_code) = TRIM(r.code)
WHERE c.icd_code IS NOT NULL
  AND TRIM(c.icd_code) != ''
  AND r.code IS NULL
