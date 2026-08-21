MODEL (
  name silver.medication_dispense_satusehat,
  kind FULL,
  grain (frappe_doc_name)
);

-- JOINED layer for medication_dispense. See diagnostic_report_satusehat.sql
-- for the full pattern explanation.
--
-- Like encounter, this resource has the two-stage status split:
--   * frappe_status (parent's raw `status`): local Frappe workflow state.
--   * fhir_status (FHIR fragment): SatuSehat transmission confirmation.
-- Relevant for gold's fct_allergy_violation (metric 3.2) -- a dispense
-- should probably only be checked against active allergies once it's past
-- frappe_status='Valid', otherwise you're flagging drafts.
--
-- NOTE: parent has no `satusehat_id` column for this resource (unlike most
-- others) -- f.fhir_id is the only identifier available, so
-- id_consistency_flag is not computed here (nothing to compare fhir_id
-- against on the parent side).
--
-- NOTE: parent has no `encounter_satusehat` column either -- linkage back
-- to the encounter for this resource goes through
-- `medication_request_satusehat` -> ... -> encounter, or via
-- `satusehat_encounter_id` (text id, not a joinable FK) as a fallback.

WITH parent AS (
    SELECT *
    FROM silver.medication_dispense_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.medication_dispense_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.medication_dispense_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    -- linkage
    p.medication_request_satusehat,
    p.satusehat_encounter_id,
    p.patient_name,
    p.patient_ihs,
    p.practitioner_ihs,

    -- two-stage status
    p.status                        AS frappe_status,
    f.fhir_status,

    -- clinical content (canonical from FHIR fragment)
    f.fhir_id,
    f.identifier_value,
    f.medication_ref,
    f.subject_ref,
    f.context_ref,
    f.when_handed_over,
    f.authorizing_prescription_ref,
    f.dosage_text,

    -- transmission outcome
    a.submission_http_status,
    a.response_resource_type,
    a.is_submission_error,
    a.error_severity,
    a.error_code,
    a.error_message,
    a.submitted_resource_id,
    a.submitted_last_updated,
    a.submitted_version_id

FROM parent p
LEFT JOIN fhir  f ON p.name = f.frappe_doc_name
LEFT JOIN audit a ON p.name = a.name
