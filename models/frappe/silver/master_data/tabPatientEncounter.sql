MODEL (
  name silver.tabPatientEncounter,
  kind FULL,
  grain (name)
);

-- Preprocessing only: cleaned CURRENT-STATE snapshot of bronze.tabPatientEncounter.
-- Table name kept identical to bronze/upstream MariaDB source (tabPatientEncounter)
-- so lineage stays 1:1 -- no renaming, no reshaping.
-- Treated as parent-only: current raw dump shows no related child table for
-- Patient Encounter, so no child_table/ model exists yet. If a child table
-- shows up upstream later, add it under models/silver/patient_encounter/child_table/.
--
-- Why the QUALIFY dedup exists: sample data shows encounters get re-modified
-- after creation (e.g. HLC-ENC-2026-00002: created 17:21, modified next day
-- 10:45). bronze is INCREMENTAL_BY_TIME_RANGE keyed on `modified`, so each
-- edit can land as a separate row per `name` across load windows. Without
-- dedup, `grain (name)` above is a label SQLMesh won't actually be able to
-- verify. This QUALIFY keeps only the latest row per `name`.
--
-- Two things intentionally NOT handled here (belong in gold, not silver):
--   * amended_from chains -- Frappe's cancel+amend pattern (docstatus 2 -> new
--     doc referencing amended_from) means an amended encounter and its
--     cancelled predecessor can both exist as separate `name` values. Silver
--     dedups per `name`, not per amendment lineage -- gold needs to walk
--     amended_from to avoid double-counting revenue/visits.
--   * `invoiced` = 0 on Completed+submitted encounters -- seen across every
--     row in the sample. Likely signal for revenue-assurance ("completed
--     visit never billed"), not a cleaning concern -- surface it as a gold
--     audit rule, not a silver transformation.
-- Changes vs. raw bronze:
--   * Keep only the most-recently-modified row per `name` (current state).
--   * VARCHAR columns: TRIM()'d, blank string ('') -> NULL.
--   * No casing changes, no business logic
--     (joins happen in models/silver/join, business rules in gold).

SELECT
    NULLIF(TRIM(name), '') AS name,
    creation,
    modified,
    NULLIF(TRIM(modified_by), '') AS modified_by,
    NULLIF(TRIM(owner), '') AS owner,
    docstatus,
    idx,
    NULLIF(TRIM(naming_series), '') AS naming_series,
    NULLIF(TRIM(title), '') AS title,
    NULLIF(TRIM(appointment), '') AS appointment,
    NULLIF(TRIM(appointment_type), '') AS appointment_type,
    NULLIF(TRIM(patient), '') AS patient,
    NULLIF(TRIM(patient_name), '') AS patient_name,
    NULLIF(TRIM(patient_sex), '') AS patient_sex,
    NULLIF(TRIM(patient_age), '') AS patient_age,
    NULLIF(TRIM(inpatient_record), '') AS inpatient_record,
    NULLIF(TRIM(inpatient_status), '') AS inpatient_status,
    NULLIF(TRIM(company), '') AS company,
    NULLIF(TRIM(status), '') AS status,
    encounter_date,
    NULLIF(TRIM(encounter_time), '') AS encounter_time,
    NULLIF(TRIM(practitioner), '') AS practitioner,
    NULLIF(TRIM(practitioner_name), '') AS practitioner_name,
    NULLIF(TRIM(medical_department), '') AS medical_department,
    NULLIF(TRIM(google_meet_link), '') AS google_meet_link,
    invoiced,
    submit_orders_on_save,
    symptoms_in_print,
    diagnosis_in_print,
    NULLIF(TRIM(therapy_plan), '') AS therapy_plan,
    NULLIF(TRIM(encounter_comment), '') AS encounter_comment,
    NULLIF(TRIM(amended_from), '') AS amended_from,
    NULLIF(TRIM(_user_tags), '') AS _user_tags,
    NULLIF(TRIM(_comments), '') AS _comments,
    NULLIF(TRIM(_assign), '') AS _assign,
    NULLIF(TRIM(_liked_by), '') AS _liked_by,
    NULLIF(TRIM(_seen), '') AS _seen,
    NULLIF(TRIM(satusehat_resource_type), '') AS satusehat_resource_type,
    NULLIF(TRIM(fhir_status), '') AS fhir_status,
    NULLIF(TRIM(satusehat_resource_id), '') AS satusehat_resource_id
FROM bronze.tabPatientEncounter
QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
