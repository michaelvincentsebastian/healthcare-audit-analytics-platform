# models/bronze/encounter/patient_encounter_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.encounter.patient_encounter import fetch_patient_encounters

@model(
    "bronze.patient_encounter_data",
    kind={
        "name": ModelKindName.INCREMENTAL_BY_TIME_RANGE,
        "time_column": "modified",
    },
    columns={
        "name": "TEXT",
        "owner": "TEXT",
        "creation": "TIMESTAMP",
        "modified": "TIMESTAMP",
        "modified_by": "TEXT",
        "docstatus": "INT",
        "idx": "INT",
        "naming_series": "TEXT",
        "title": "TEXT",
        "appointment": "TEXT",
        "appointment_type": "TEXT",
        "patient": "TEXT",
        "patient_name": "TEXT",
        "patient_sex": "TEXT",
        "patient_age": "TEXT",
        "inpatient_record": "TEXT",
        "inpatient_status": "TEXT",
        "company": "TEXT",
        "status": "TEXT",
        "encounter_date": "DATE",
        "encounter_time": "TEXT",
        "practitioner": "TEXT",
        "practitioner_name": "TEXT",
        "medical_department": "TEXT",
        "google_meet_link": "TEXT",
        "invoiced": "INT",
        "submit_orders_on_save": "INT",
        "symptoms_in_print": "INT",
        "diagnosis_in_print": "INT",
        "therapy_plan": "TEXT",
        "encounter_comment": "TEXT",
        "amended_from": "TEXT",
        "satusehat_resource_id": "TEXT",
        "fhir_status": "TEXT",
        "satusehat_resource_type": "TEXT",
    },
)
def execute(context, start, end, execution_time, **kwargs):
    with FrappeClient() as client:
        records = fetch_patient_encounters(client, start=start, end=end)

    if not records:
        yield from ()
        return

    yield pd.DataFrame(records)
