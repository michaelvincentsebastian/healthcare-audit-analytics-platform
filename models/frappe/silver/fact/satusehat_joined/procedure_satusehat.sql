MODEL (
  name silver.procedure_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for procedure. See diagnostic_report_satusehat.sql for the
-- full pattern explanation. `clinical_procedure` is a local Frappe
-- DocType link with no FHIR fragment equivalent, kept from parent as-is
-- (this is the ICD-9-CM-relevant field gold's fct_uncoded_encounter can
-- chain to, alongside stg_condition, per the earlier PRD discussion).

WITH parent AS (
    SELECT *
    FROM silver.procedure_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.procedure_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.procedure_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    p.encounter_satusehat,
    p.clinical_procedure,
    p.patient,
    p.patient_name,
    p.patient_ihs,
    p.practitioner_ihs,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.status                        AS resource_status,
    f.category_code,
    f.code,
    f.code_display,
    f.subject_ref,
    f.encounter_ref,
    f.performer_ref,

    -- frappe-side raw input, kept for comparison against f.code/code_display
    p.procedure_code,
    p.procedure_display,

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
