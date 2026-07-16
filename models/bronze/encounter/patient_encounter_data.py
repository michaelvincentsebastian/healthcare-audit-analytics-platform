# models/bronze/patient_encounter_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.encounter.patient_encounter import fetch_patient_encounters

@model(
    "bronze.patient_encounter_data",
    kind=ModelKindName.FULL,
    columns={
        "name": "text",
        "owner": "text",
        "creation": "timestamp",
        "modified": "timestamp",
        "modified_by": "text",
        "docstatus": "int",
        "idx": "int",
        "naming_series": "text",
        "title": "text",
        "patient": "text",
        "patient_name": "text",
        "patient_sex": "text",
        "patient_age": "text",
        "inpatient_status": "text",
        "company": "text",
        "status": "text",
        "encounter_date": "date",
        "encounter_time": "time",
        "practitioner": "text",
        "practitioner_name": "text",
        "invoiced": "int",
        "submit_orders_on_save": "int",
        "symptoms_in_print": "int",
        "diagnosis_in_print": "int",
        "doctype": "text",
        "lab_test_prescription": "json",
        "diagnosis": "json",
        "procedure_prescription": "json",
        "codification_table": "json",
        "therapies": "json",
        "symptoms": "json",
        "drug_prescription": "json",
    },
)
def execute(context, start, end, execution_time, **kwargs) -> pd.DataFrame:
    with FrappeClient() as client:
        records = fetch_patient_encounters(client, start=start, end=end)
    return pd.DataFrame(records)