MODEL (
  name bronze.tabPatient,
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
  patient_name::VARCHAR AS patient_name,
  sex::VARCHAR AS sex,
  blood_group::VARCHAR AS blood_group,
  dob::DATE AS dob,
  image::VARCHAR AS image,
  status::VARCHAR AS status,
  uid::VARCHAR AS uid,
  inpatient_record::VARCHAR AS inpatient_record,
  inpatient_status::VARCHAR AS inpatient_status,
  report_preference::VARCHAR AS report_preference,
  mobile::VARCHAR AS mobile,
  phone::VARCHAR AS phone,
  email::VARCHAR AS email,
  invite_user::INTEGER AS invite_user,
  user_id::VARCHAR AS user_id,
  customer::VARCHAR AS customer,
  customer_group::VARCHAR AS customer_group,
  territory::VARCHAR AS territory,
  default_currency::VARCHAR AS default_currency,
  default_price_list::VARCHAR AS default_price_list,
  language::VARCHAR AS language,
  patient_details::VARCHAR AS patient_details,
  occupation::VARCHAR AS occupation,
  marital_status::VARCHAR AS marital_status,
  allergies::VARCHAR AS allergies,
  medication::VARCHAR AS medication,
  medical_history::VARCHAR AS medical_history,
  surgical_history::VARCHAR AS surgical_history,
  tobacco_past_use::VARCHAR AS tobacco_past_use,
  tobacco_current_use::VARCHAR AS tobacco_current_use,
  alcohol_past_use::VARCHAR AS alcohol_past_use,
  alcohol_current_use::VARCHAR AS alcohol_current_use,
  surrounding_factors::VARCHAR AS surrounding_factors,
  other_risk_factors::VARCHAR AS other_risk_factors,
  _user_tags::VARCHAR AS _user_tags,
  _comments::VARCHAR AS _comments,
  _assign::VARCHAR AS _assign,
  _liked_by::VARCHAR AS _liked_by,
  satusehat_resource_type::VARCHAR AS satusehat_resource_type,
  satusehat_id::VARCHAR AS satusehat_id,
  fhir_status::VARCHAR AS fhir_status,
  satusehat_resource_id::VARCHAR AS satusehat_resource_id
FROM frappe_bridge.bridge.tabpatient
WHERE modified >= @start_ds AND modified < @end_ds;
