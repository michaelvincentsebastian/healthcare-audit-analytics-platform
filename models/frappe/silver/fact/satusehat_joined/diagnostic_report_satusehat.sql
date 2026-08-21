MODEL (
  name silver.diagnostic_report_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer: combines the three diagnostic_report fragments into one
-- gold-ready row per resource submission.
--   * parent = silver.diagnostic_report_satusehat_data_clean            (frappe-side fields)
--   * fhir   = silver.diagnostic_report_fhir_resource                   (flattened FHIR clinical fields)
--   * audit  = silver.diagnostic_report_satusehat_data_submission_audit (parsed api_response)
--
-- Join key: name (parent/audit) = frappe_doc_name (fhir fragment).
-- All three sources are dedup'd to the latest `modified` snapshot BEFORE
-- joining -- upstream bronze/view models are incremental snapshots, so the
-- same resource re-validated or re-submitted can legitimately appear more
-- than once in any of the three fragments.
--
-- Column precedence when the same concept exists in more than one fragment:
--   * identity/lineage (name, creation, modified, docstatus, owner) -> parent
--   * linkage keys (encounter_satusehat, servicerequest_satusehat,
--     specimen_satusehat, observation_satusehat, patient_ihs, ...)   -> parent
--     (identical value across all 3 fragments; parent chosen as canonical)
--   * clinical content (status, code, dates, refs)                  -> fhir fragment
--     (FHIR-native semantics, richer than the frappe-side columns)
--   * transmission outcome (http status, error detail)              -> audit
--
-- Data-quality flag added at THIS layer (not upstream -- this is a
-- cross-fragment consistency check, not a per-source cleaning rule):
--   * id_consistency_flag: parent.satusehat_id (what Frappe recorded as the
--     confirmed SatuSehat ID) should equal fhir.fhir_id (the `id` inside the
--     FHIR resource body itself) once a resource has actually round-tripped.
--     A non-null mismatch means something is corrupted between what Frappe
--     stored and what payload_json actually contains -- flagged here so
--     gold doesn't have to re-derive it.

WITH parent AS (
    SELECT *
    FROM silver.diagnostic_report_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.diagnostic_report_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.diagnostic_report_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    -- linkage (canonical from parent; identical across fragments)
    p.encounter_satusehat,
    p.servicerequest_satusehat,
    p.specimen_satusehat,
    p.observation_satusehat,
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
    f.effective_datetime,
    f.issued,
    f.performer_ref,
    f.based_on_ref,
    f.conclusion_code,

    -- frappe-side display fields with no FHIR ViewDefinition equivalent
    p.report_code,
    p.report_display,
    p.conclusion_display,

    -- transmission outcome (from audit)
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

    -- cross-fragment data-quality flag
    CASE
        WHEN p.satusehat_id IS NOT NULL
         AND f.fhir_id IS NOT NULL
         AND p.satusehat_id != f.fhir_id
            THEN TRUE
        ELSE FALSE
    END AS id_consistency_flag

FROM parent p
LEFT JOIN fhir  f ON p.name = f.frappe_doc_name
LEFT JOIN audit a ON p.name = a.name
