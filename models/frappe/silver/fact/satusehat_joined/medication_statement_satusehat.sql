MODEL (
  name silver.medication_statement_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for medication_statement. See diagnostic_report_satusehat.sql
-- for the full pattern explanation. `item_code` is a local Frappe Item
-- link with no FHIR fragment equivalent, kept from parent as-is.

WITH parent AS (
    SELECT *
    FROM silver.medication_statement_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.medication_statement_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.medication_statement_satusehat_data_submission_audit
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

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.status                        AS resource_status,
    f.category_code,
    f.medication_code,
    f.medication_display,
    f.subject_ref,
    f.context_ref,
    f.date_asserted,
    f.information_source_ref,
    f.note_text,

    -- frappe-side field with no FHIR fragment equivalent
    p.item_code,

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
