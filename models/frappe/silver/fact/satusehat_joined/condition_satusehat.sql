MODEL (
  name silver.condition_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for condition. See diagnostic_report_satusehat.sql for the
-- full pattern explanation.
--
-- NOTE: parent carries BOTH `patient_encounter` (local FK) and
-- `encounter_satusehat` (staging FK) -- the only resource besides
-- encounter itself with two encounter-linkage columns. Per your call,
-- we drop `patient_encounter` here and keep `encounter_satusehat` only,
-- since the dev's own design intent was for every downstream doctype to
-- hang off encounter_satusehat consistently -- patient_encounter on this
-- table was a stray/inconsistent field, not an intentional second grain.

WITH parent AS (
    SELECT *
    FROM silver.condition_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.condition_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.condition_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    -- linkage: encounter_satusehat only (patient_encounter intentionally dropped)
    p.encounter_satusehat,
    p.patient_name,
    p.patient_ihs,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.clinical_status,
    f.category_code,
    f.code,
    f.code_display,
    f.subject_ref,
    f.subject_display,
    f.encounter_ref,

    -- frappe-side raw input, kept for comparison against f.code/code_display
    p.icd_code,
    p.diagnosis_display,
    p.validation_status,

    -- transmission outcome
    p.satusehat_id,
    a.submission_http_status,
    a.response_resource_type,
    a.is_submission_error,
    a.error_severity,
    a.error_code,
    a.error_message,
    a.submitted_resource_id,
    a.submitted_last_updated,
    a.submitted_version_id,

    CASE
        WHEN p.satusehat_id IS NOT NULL AND f.fhir_id IS NOT NULL AND p.satusehat_id != f.fhir_id
            THEN TRUE ELSE FALSE
    END AS id_consistency_flag

FROM parent p
LEFT JOIN fhir  f ON p.name = f.frappe_doc_name
LEFT JOIN audit a ON p.name = a.name
