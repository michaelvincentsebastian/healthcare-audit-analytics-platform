MODEL (
  name silver.tabPatient,
  kind FULL,
  grain (name)
);

-- Preprocessing only: cleaned CURRENT-STATE snapshot of bronze.tabPatient.
-- Table name kept identical to bronze/upstream MariaDB source (tabPatient)
-- so lineage stays 1:1 -- no renaming, no reshaping.
--
-- Why the QUALIFY dedup exists: bronze is INCREMENTAL_BY_TIME_RANGE keyed on
-- `modified`, so a patient record edited more than once can legitimately
-- produce >1 row per `name` across load windows. Without dedup, `grain (name)`
-- above is a label SQLMesh won't actually be able to verify. This QUALIFY
-- keeps only the latest row per `name`.
--
-- PII note: `uid` and `nik`-style national ID values live in this table
-- unmasked (needed for SatuSehat matching). Treat silver.tabPatient as
-- restricted-access; if a gold-layer audit dashboard needs patient identity,
-- prefer joining on `name`/`satusehat_id` and masking uid/nik at that layer
-- rather than exposing them directly on a dashboard.
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
    NULLIF(TRIM(first_name), '') AS first_name,
    NULLIF(TRIM(middle_name), '') AS middle_name,
    NULLIF(TRIM(last_name), '') AS last_name,
    NULLIF(TRIM(patient_name), '') AS patient_name,
    NULLIF(TRIM(sex), '') AS sex,
    NULLIF(TRIM(blood_group), '') AS blood_group,
    dob,
    NULLIF(TRIM(image), '') AS image,
    NULLIF(TRIM(status), '') AS status,
    NULLIF(TRIM(uid), '') AS uid,
    NULLIF(TRIM(inpatient_record), '') AS inpatient_record,
    NULLIF(TRIM(inpatient_status), '') AS inpatient_status,
    NULLIF(TRIM(report_preference), '') AS report_preference,
    NULLIF(TRIM(mobile), '') AS mobile,
    NULLIF(TRIM(phone), '') AS phone,
    NULLIF(TRIM(email), '') AS email,
    invite_user,
    NULLIF(TRIM(user_id), '') AS user_id,
    NULLIF(TRIM(customer), '') AS customer,
    NULLIF(TRIM(customer_group), '') AS customer_group,
    NULLIF(TRIM(territory), '') AS territory,
    NULLIF(TRIM(default_currency), '') AS default_currency,
    NULLIF(TRIM(default_price_list), '') AS default_price_list,
    NULLIF(TRIM(language), '') AS language,
    NULLIF(TRIM(patient_details), '') AS patient_details,
    NULLIF(TRIM(occupation), '') AS occupation,
    NULLIF(TRIM(marital_status), '') AS marital_status,
    NULLIF(TRIM(allergies), '') AS allergies,
    NULLIF(TRIM(medication), '') AS medication,
    NULLIF(TRIM(medical_history), '') AS medical_history,
    NULLIF(TRIM(surgical_history), '') AS surgical_history,
    NULLIF(TRIM(tobacco_past_use), '') AS tobacco_past_use,
    NULLIF(TRIM(tobacco_current_use), '') AS tobacco_current_use,
    NULLIF(TRIM(alcohol_past_use), '') AS alcohol_past_use,
    NULLIF(TRIM(alcohol_current_use), '') AS alcohol_current_use,
    NULLIF(TRIM(surrounding_factors), '') AS surrounding_factors,
    NULLIF(TRIM(other_risk_factors), '') AS other_risk_factors,
    NULLIF(TRIM(_user_tags), '') AS _user_tags,
    NULLIF(TRIM(_comments), '') AS _comments,
    NULLIF(TRIM(_assign), '') AS _assign,
    NULLIF(TRIM(_liked_by), '') AS _liked_by,
    NULLIF(TRIM(satusehat_resource_type), '') AS satusehat_resource_type,
    NULLIF(TRIM(satusehat_id), '') AS satusehat_id,
    NULLIF(TRIM(fhir_status), '') AS fhir_status,
    NULLIF(TRIM(satusehat_resource_id), '') AS satusehat_resource_id
FROM bronze.tabPatient
QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1

