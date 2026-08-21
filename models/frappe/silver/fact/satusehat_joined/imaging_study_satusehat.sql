MODEL (
  name silver.imaging_study_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for imaging_study. See diagnostic_report_satusehat.sql for
-- the full pattern explanation.
--
-- NOTE (exception to the general "everything hangs off encounter_satusehat"
-- pattern): imaging_study has NO `encounter_satusehat` FK column at all --
-- it only links via `servicerequest_satusehat`. To reach the encounter from
-- here, gold needs to chain through service_request_satusehat first
-- (encounter_satusehat -> servicerequest -> imaging_study), same chain
-- shape as specimen -> diagnostic_report. `satusehat_encounter_id` /
-- `satusehat_servicerequest_id` here are the already-confirmed SatuSehat
-- IDs (text), kept for convenience but they are not FK join keys into
-- other silver tables (those use the frappe doc name, not the satusehat id).

WITH parent AS (
    SELECT *
    FROM silver.imaging_study_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.imaging_study_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.imaging_study_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    -- linkage: via service request, NOT a direct encounter FK (see note above)
    p.servicerequest_satusehat,
    p.satusehat_encounter_id,
    p.satusehat_servicerequest_id,
    p.patient_name,
    p.patient_ihs,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.identifier_value,
    f.status                        AS resource_status,
    f.subject_ref,
    f.encounter_ref,
    f.started,
    f.based_on_ref,
    f.modality_code,
    f.number_of_series,
    f.number_of_instances,

    -- frappe-side fields with no FHIR fragment equivalent
    p.modality_display,
    p.dicom_uid,

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
