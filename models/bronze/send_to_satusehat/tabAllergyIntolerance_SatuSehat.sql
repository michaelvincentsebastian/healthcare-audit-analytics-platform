MODEL (
  name bronze.tabAllergyIntolerance_SatuSehat,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column modified
  ),
  grain ('name', 'modified'),
);

-- Bridge ke MariaDB via DuckDB Quack server (lihat analytics-bridge repo).
-- IF NOT EXISTS supaya aman kalau session yang sama sudah pernah attach.
ATTACH IF NOT EXISTS 'quack:localhost:9494' AS frappe_bridge (
    TYPE quack,
    TOKEN @quack_token(),
    DISABLE_SSL true
);

-- Bronze = raw & complete: explicit mapping based on dump.json
SELECT
  name::VARCHAR AS name,
  creation::TIMESTAMP AS creation,
  modified::TIMESTAMP AS modified,
  modified_by::VARCHAR AS modified_by,
  owner::VARCHAR AS owner,
  docstatus::INTEGER AS docstatus,
  idx::INTEGER AS idx,
  encounter_satusehat::VARCHAR AS encounter_satusehat,
  patient_name::VARCHAR AS patient_name,
  patient_ihs::VARCHAR AS patient_ihs,
  practitioner_ihs::VARCHAR AS practitioner_ihs,
  satusehat_encounter_id::VARCHAR AS satusehat_encounter_id,
  clinical_status::VARCHAR AS clinical_status,
  verification_status::VARCHAR AS verification_status,
  category::VARCHAR AS category,
  snomed_code::VARCHAR AS snomed_code,
  snomed_display::VARCHAR AS snomed_display,
  allergy_text::VARCHAR AS allergy_text,
  status::VARCHAR AS status,
  satusehat_id::VARCHAR AS satusehat_id,
  api_response::VARCHAR AS api_response,
  _user_tags::VARCHAR AS _user_tags,
  _comments::VARCHAR AS _comments,
  _assign::VARCHAR AS _assign,
  _liked_by::VARCHAR AS _liked_by,
  payload_json::VARCHAR AS payload_json
FROM frappe_bridge.bridge.taballergyintolerance_satusehat
WHERE modified >= @start_ds AND modified < @end_ds;
