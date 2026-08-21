MODEL (
  name silver.observation_satusehat,
  kind FULL,
  grain (frappe_doc_name, observation_idx)
);

-- JOINED layer for observation. See diagnostic_report_satusehat.sql for the
-- general pattern -- this one is structurally different from all other 15
-- resources:
--
--   * One Frappe doc (vital signs form) submits MULTIPLE Observation
--     resources at once (temperature, pulse, BP, etc in one payload array).
--   * parent (`observation_satusehat_data_clean`) is still 1 row per doc
--     (dedup by `name` only, same as everywhere else).
--   * fhir fragment is 1 row per (frappe_doc_name, observation_idx) --
--     already exploded by the flattener, so the parent->fhir join here is
--     intentionally ONE-TO-MANY (fan-out), not 1:1 like other resources.
--   * audit fragment is 1 row per (name, response_idx), where response_idx
--     is index-aligned with observation_idx (same array order in the
--     source payload) -- so we join on BOTH the doc name AND the index,
--     not on doc name alone, or every vital sign would get every doc's
--     audit rows duplicated against each other.
--
-- Practical effect for gold: the same submission_http_status /
-- is_submission_error will legitimately repeat across every observation_idx
-- belonging to the same doc when the whole array was accepted/rejected
-- together -- that's correct, not a dedup bug, since SatuSehat responds to
-- the batch as a whole in most cases. If a future payload shape allows
-- partial batch failure (some vital signs accepted, others not), that will
-- already show up correctly here too, since the join is per-index.
--
-- `p.satusehat_ids` (plural, comma-joined string on the parent) is kept
-- raw for reference, but f.fhir_id (singular, per observation_idx) is the
-- canonical per-row identifier -- don't try to split satusehat_ids
-- yourself, f.fhir_id already gives you the correct 1:1 value.

WITH parent AS (
    SELECT *
    FROM silver.observation_satusehat_data_clean
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
),
fhir AS (
    SELECT *
    FROM silver.observation_fhir_resource
    QUALIFY ROW_NUMBER() OVER (PARTITION BY frappe_doc_name, observation_idx ORDER BY modified DESC) = 1
),
audit AS (
    SELECT *
    FROM silver.observation_satusehat_data_submission_audit
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name, response_idx ORDER BY modified DESC) = 1
)

SELECT
    p.name                          AS frappe_doc_name,
    f.observation_idx,
    p.creation,
    p.modified,
    p.docstatus,
    p.owner,

    p.encounter_satusehat,
    p.patient,
    p.patient_name,
    p.patient_ihs,
    p.practitioner_ihs,
    p.validation_status,

    -- clinical content (canonical from FHIR fragment, per vital sign)
    f.fhir_id,
    f.status                        AS resource_status,
    f.category_code,
    f.code,
    f.code_display,
    f.subject_ref,
    f.encounter_ref,
    f.performer_ref,
    f.effective_datetime,
    f.value,
    f.unit,

    -- frappe-side raw field, kept for reference only (do not re-split; see header note)
    p.satusehat_ids,
    p.vital_signs,

    -- transmission outcome (per observation_idx, aligned via response_idx)
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
INNER JOIN fhir f
  ON p.name = f.frappe_doc_name
LEFT JOIN audit a
  ON p.name = a.name
 AND f.observation_idx = a.response_idx
