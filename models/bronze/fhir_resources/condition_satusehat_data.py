# models/bronze/encounter_satusehat_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.fhir_resources.condition_satusehat import fetch_condition_satusehat

@model(
    "bronze.condition_satusehat_data",
    kind=ModelKindName.FULL,
    columns={
        "name": "text",
        "owner": "text",
        "creation": "timestamp",
        "modified": "timestamp",
        "modified_by": "text",
        "docstatus": "int",
        "idx": "int",
        "encounter_satusehat": "text",
        "patient_encounter": "text",
        "patient": "text",
        "patient_name": "text",
        "patient_ihs": "text",
        "satusehat_encounter_id": "text",
        "icd_code": "text",
        "diagnosis_display": "text",
        "validation_status": "text",
        "satusehat_id": "text",
        "api_response": "text",
        "payload_json": "text",
        "doctype": "text",
    },
)
def execute(context, start, end, execution_time, **kwargs) -> pd.DataFrame:
    with FrappeClient() as client:
        records = fetch_condition_satusehat(client)
    return pd.DataFrame(records)