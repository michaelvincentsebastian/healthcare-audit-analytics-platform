MODEL (
  name silver.questionnaire_response_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for questionnaire_response. See diagnostic_report_satusehat.sql
-- for the full pattern explanation. `keluhan_utama` and `riwayat_alergi`
-- exist on BOTH parent (raw input) and the FHIR fragment (round-tripped) --
-- prefer the FHIR fragment as canonical, same precedence rule as everywhere
-- else. `questionnaire_url` (parent) is kept separately from `f.questionnaire`
-- (the code/canonical URL actually embedded in the resource) for comparison.

WITH parent AS (
    SELECT *
    FROM silver.questionnaire_response_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.questionnaire_response_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.questionnaire_response_satusehat_data_submission_audit
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
    f.status                        AS resource_status,
    f.questionnaire,
    f.subject_ref,
    f.encounter_ref,
    f.authored,
    f.author_ref,
    f.source_ref,
    f.keluhan_utama,
    f.riwayat_alergi,

    -- frappe-side raw input, kept for comparison
    p.questionnaire_url,
    p.authored_datetime,

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
