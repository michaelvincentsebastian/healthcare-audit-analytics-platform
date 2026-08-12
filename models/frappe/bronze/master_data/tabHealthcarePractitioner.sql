MODEL (
  name bronze.tabHealthcarePractitioner,
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
  naming_series::VARCHAR AS naming_series,
  first_name::VARCHAR AS first_name,
  middle_name::VARCHAR AS middle_name,
  last_name::VARCHAR AS last_name,
  practitioner_name::VARCHAR AS practitioner_name,
  gender::VARCHAR AS gender,
  image::VARCHAR AS image,
  status::VARCHAR AS status,
  mobile_phone::VARCHAR AS mobile_phone,
  residence_phone::VARCHAR AS residence_phone,
  office_phone::VARCHAR AS office_phone,
  practitioner_type::VARCHAR AS practitioner_type,
  employee::VARCHAR AS employee,
  supplier::VARCHAR AS supplier,
  department::VARCHAR AS department,
  designation::VARCHAR AS designation,
  user_id::VARCHAR AS user_id,
  hospital::VARCHAR AS hospital,
  google_calendar::VARCHAR AS google_calendar,
  op_consulting_charge_item::VARCHAR AS op_consulting_charge_item,
  op_consulting_charge::DECIMAL(21,9) AS op_consulting_charge,
  inpatient_visit_charge_item::VARCHAR AS inpatient_visit_charge_item,
  inpatient_visit_charge::DECIMAL(21,9) AS inpatient_visit_charge,
  default_currency::VARCHAR AS default_currency,
  practitioner_primary_contact::VARCHAR AS practitioner_primary_contact,
  mobile_no::VARCHAR AS mobile_no,
  email_id::VARCHAR AS email_id,
  practitioner_primary_address::VARCHAR AS practitioner_primary_address,
  primary_address::VARCHAR AS primary_address,
  _user_tags::VARCHAR AS _user_tags,
  _comments::VARCHAR AS _comments,
  _assign::VARCHAR AS _assign,
  _liked_by::VARCHAR AS _liked_by,
  satusehat_resource_type::VARCHAR AS satusehat_resource_type,
  nik::VARCHAR AS nik,
  satusehat_id::VARCHAR AS satusehat_id,
  fhir_status::VARCHAR AS fhir_status,
  satusehat_resource_id::VARCHAR AS satusehat_resource_id
FROM frappe_bridge.bridge.tabhealthcare_practitioner
WHERE modified >= @start_ds AND modified < @end_ds;
