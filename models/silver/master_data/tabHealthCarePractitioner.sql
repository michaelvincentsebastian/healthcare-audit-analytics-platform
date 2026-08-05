MODEL (
  name bronze.tabPatientEncounter,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column modified
  ),
  grain ('name', 'modified'),
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
  title::VARCHAR AS title,
  appointment::VARCHAR AS appointment,
  appointment_type::VARCHAR AS appointment_type,
  patient::VARCHAR AS patient,
  patient_name::VARCHAR AS patient_name,
  patient_sex::VARCHAR AS patient_sex,
  patient_age::VARCHAR AS patient_age,
  inpatient_record::VARCHAR AS inpatient_record,
  inpatient_status::VARCHAR AS inpatient_status,
  company::VARCHAR AS company,
  status::VARCHAR AS status,
  encounter_date::DATE AS encounter_date,
  encounter_time::VARCHAR AS encounter_time,
  practitioner::VARCHAR AS practitioner,
  practitioner_name::VARCHAR AS practitioner_name,
  medical_department::VARCHAR AS medical_department,
  google_meet_link::VARCHAR AS google_meet_link,
  invoiced::INTEGER AS invoiced,
  submit_orders_on_save::INTEGER AS submit_orders_on_save,
  symptoms_in_print::INTEGER AS symptoms_in_print,
  diagnosis_in_print::INTEGER AS diagnosis_in_print,
  therapy_plan::VARCHAR AS therapy_plan,
  encounter_comment::VARCHAR AS encounter_comment,
  amended_from::VARCHAR AS amended_from,
  _user_tags::VARCHAR AS _user_tags,
  _comments::VARCHAR AS _comments,
  _assign::VARCHAR AS _assign,
  _liked_by::VARCHAR AS _liked_by,
  _seen::VARCHAR AS _seen,
  satusehat_resource_type::VARCHAR AS satusehat_resource_type,
  fhir_status::VARCHAR AS fhir_status,
  satusehat_resource_id::VARCHAR AS satusehat_resource_id
FROM frappe_bridge.bridge.tabpatient_encounter
WHERE modified >= @start_ds AND modified < @end_ds;
