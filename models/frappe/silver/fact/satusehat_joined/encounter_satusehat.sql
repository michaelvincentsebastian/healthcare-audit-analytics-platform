MODEL (
  name silver.encounter_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for encounter. See diagnostic_report_satusehat.sql for the
-- full pattern explanation.
--
-- This is the ONLY resource where the two-stage status distinction matters
-- for gold's fct_bridging_completion:
--   * frappe_status (from parent's raw `status` column): Waiting / Valid /
--     Deleted -- the LOCAL manual-validation workflow state in the Frappe
--     app. `Deleted` means a staff member rejected the record during
--     validation (and it's gone from bronze going forward, not a bug).
--   * fhir_status (from the FHIR fragment): whether the resource actually
--     `arrived` at SatuSehat -- the TRANSMISSION confirmation, independent
--     of the local validation decision.
--   A row with frappe_status='Valid' but fhir_status NOT 'arrived' is the
--   real "unsent queue" case (passed manual validation, failed transmission).
--
-- `patient_encounter` is kept here (unlike condition) because on THIS
-- resource it is the correct, intentional FK back to the local
-- tabPatientEncounter doc -- it's the field fct_bridging_completion needs
-- to compute total_local_encounter vs. total_arrived.

WITH parent AS (
    SELECT *
    FROM silver.encounter_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.encounter_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.encounter_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    -- linkage: the local encounter this staging row represents
    p.patient_encounter,
    p.patient,
    p.patient_name,
    p.patient_ihs,
    p.practitioner,
    p.practitioner_name,
    p.practitioner_ihs,
    p.organization_id,
    p.location_id,

    -- two-stage status (see header note above)
    p.status                        AS frappe_status,
    f.fhir_status,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.identifier_value,
    f.class_code,
    f.class_display,
    f.subject_ref,
    f.subject_display,
    f.period_start,
    f.period_end,
    f.location_ref,
    f.service_provider_ref,

    -- frappe-side raw input, kept for comparison against f.period_start
    p.start_time,

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
