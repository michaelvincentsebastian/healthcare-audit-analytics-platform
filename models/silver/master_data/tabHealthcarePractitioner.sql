MODEL (
  name silver.tabHealthcarePractitioner,
  kind FULL,
  grain (name)
);

-- Preprocessing only: cleaned CURRENT-STATE snapshot of bronze.tabHealthcarePractitioner.
-- Table name kept identical to bronze/upstream MariaDB source (tabHealthcarePractitioner)
-- so lineage stays 1:1 -- no renaming, no reshaping.
--
-- Why the QUALIFY dedup exists (found via sample data review):
--   bronze is INCREMENTAL_BY_TIME_RANGE keyed on `modified`, so a doc that gets
--   edited more than once will legitimately produce >1 row per `name` across
--   different load windows (that's correct bronze behaviour -- it's a raw
--   history log). Without dedup here, `grain (name)` above is just a label
--   that isn't actually enforced by the query -- SQLMesh's grain audit would
--   fail (or silently pass on single-snapshot dummy data, then break once
--   someone edits a practitioner record twice). This QUALIFY keeps only the
--   latest row per `name` so silver is truly 1 row = 1 current entity.
-- Changes vs. raw bronze:
--   * Keep only the most-recently-modified row per `name` (current state).
--   * VARCHAR columns: TRIM()'d, blank string ('') -> NULL.
--   * No casing changes, no joins, no business logic
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
    NULLIF(TRIM(practitioner_name), '') AS practitioner_name,
    NULLIF(TRIM(gender), '') AS gender,
    NULLIF(TRIM(image), '') AS image,
    NULLIF(TRIM(status), '') AS status,
    NULLIF(TRIM(mobile_phone), '') AS mobile_phone,
    NULLIF(TRIM(residence_phone), '') AS residence_phone,
    NULLIF(TRIM(office_phone), '') AS office_phone,
    NULLIF(TRIM(practitioner_type), '') AS practitioner_type,
    NULLIF(TRIM(employee), '') AS employee,
    NULLIF(TRIM(supplier), '') AS supplier,
    NULLIF(TRIM(department), '') AS department,
    NULLIF(TRIM(designation), '') AS designation,
    NULLIF(TRIM(user_id), '') AS user_id,
    NULLIF(TRIM(hospital), '') AS hospital,
    NULLIF(TRIM(google_calendar), '') AS google_calendar,
    NULLIF(TRIM(op_consulting_charge_item), '') AS op_consulting_charge_item,
    op_consulting_charge,
    NULLIF(TRIM(inpatient_visit_charge_item), '') AS inpatient_visit_charge_item,
    inpatient_visit_charge,
    NULLIF(TRIM(default_currency), '') AS default_currency,
    NULLIF(TRIM(practitioner_primary_contact), '') AS practitioner_primary_contact,
    NULLIF(TRIM(mobile_no), '') AS mobile_no,
    NULLIF(TRIM(email_id), '') AS email_id,
    NULLIF(TRIM(practitioner_primary_address), '') AS practitioner_primary_address,
    NULLIF(TRIM(primary_address), '') AS primary_address,
    NULLIF(TRIM(_user_tags), '') AS _user_tags,
    NULLIF(TRIM(_comments), '') AS _comments,
    NULLIF(TRIM(_assign), '') AS _assign,
    NULLIF(TRIM(_liked_by), '') AS _liked_by,
    NULLIF(TRIM(satusehat_resource_type), '') AS satusehat_resource_type,
    NULLIF(TRIM(nik), '') AS nik,
    NULLIF(TRIM(satusehat_id), '') AS satusehat_id,
    NULLIF(TRIM(fhir_status), '') AS fhir_status,
    NULLIF(TRIM(satusehat_resource_id), '') AS satusehat_resource_id
FROM bronze.tabHealthcarePractitioner
QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
