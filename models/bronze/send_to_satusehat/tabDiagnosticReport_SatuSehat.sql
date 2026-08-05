MODEL (
  name bronze.tabDiagnosticReport_SatuSehat,
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
  servicerequest_satusehat::VARCHAR AS servicerequest_satusehat,
  specimen_satusehat::VARCHAR AS specimen_satusehat,
  observation_satusehat::VARCHAR AS observation_satusehat,
  patient_name::VARCHAR AS patient_name,
  patient_ihs::VARCHAR AS patient_ihs,
  practitioner_ihs::VARCHAR AS practitioner_ihs,
  report_code::VARCHAR AS report_code,
  report_display::VARCHAR AS report_display,
  conclusion_code::VARCHAR AS conclusion_code,
  conclusion_display::VARCHAR AS conclusion_display,
  status::VARCHAR AS status,
  satusehat_id::VARCHAR AS satusehat_id,
  api_response::VARCHAR AS api_response,
  payload_json::VARCHAR AS payload_json,
  _user_tags::VARCHAR AS _user_tags,
  _comments::VARCHAR AS _comments,
  _assign::VARCHAR AS _assign,
  _liked_by::VARCHAR AS _liked_by
FROM frappe_bridge.bridge.tabdiagnosticreport_satusehat
WHERE modified >= @start_ds AND modified < @end_ds;
