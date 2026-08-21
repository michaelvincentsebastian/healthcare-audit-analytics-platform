MODEL (
  name silver.allergy_intolerance_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for allergy_intolerance. See diagnostic_report_satusehat.sql
-- for the full pattern explanation (dedup-then-join, column precedence,
-- id_consistency_flag rationale). Notes specific to this resource:
--   * AllergyIntolerance has no single top-level `status` in FHIR -- it has
--     clinicalStatus + verificationStatus separately, so there is no
--     `resource_status` column here (unlike diagnostic_report/careplan).
--   * `p.status` (the frappe-side field) is Fixed on `encounter_satusehat`
--     -> use encounter_satusehat only for downstream joins, per your
--     confirmation (patient_encounter is not carried on this resource anyway).
--   * clinical_status / verification_status / category / code / code_display
--     come from the FHIR fragment (what was actually round-tripped),
--     preferred over parent's raw snomed_code/snomed_display/category input.

WITH parent AS (
    SELECT *
    FROM silver.allergy_intolerance_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.allergy_intolerance_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.allergy_intolerance_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    -- linkage
    p.encounter_satusehat,
    p.patient_name,
    p.patient_ihs,
    p.practitioner_ihs,

    -- workflow status (frappe-side lifecycle: e.g. Waiting/Valid/Deleted)
    p.status                        AS frappe_status,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.identifier_value,
    f.clinical_status,
    f.verification_status,
    f.category,
    f.code,
    f.code_display,
    f.patient_ref,
    f.encounter_ref,
    f.recorder_ref,

    -- frappe-side raw input, kept for audit/comparison against f.code/code_display
    p.allergy_text,

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
