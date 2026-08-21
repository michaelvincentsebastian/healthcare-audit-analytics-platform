MODEL (
  name silver.service_request_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for service_request. See diagnostic_report_satusehat.sql for
-- the full pattern explanation.
--
-- NOTE for gold's fct_diagnostic_tat (metric 3.4): neither parent nor the
-- FHIR fragment carries a priority/"cito"/stat flag -- this resource has
-- no dedicated priority column anywhere in bronze. `request_text` (free
-- text, frappe-side only) is kept in case urgency is embedded there as
-- unstructured text, but it is NOT a structured field you can filter on
-- reliably. This is a known open gap, not something this join can resolve.

WITH parent AS (
    SELECT *
    FROM silver.service_request_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.service_request_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.service_request_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    p.encounter_satusehat,
    p.patient_name,
    p.patient_ihs,
    p.practitioner_ihs,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.identifier_value,
    f.status                        AS resource_status,
    f.intent,
    f.category_code,
    f.code,
    f.code_display,
    f.subject_ref,
    f.encounter_ref,
    f.authored_on,
    f.requester_ref,
    f.performer_ref,

    -- frappe-side raw input, kept for comparison against f.code/code_display
    p.loinc_code,
    p.loinc_display,
    p.request_text,

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
