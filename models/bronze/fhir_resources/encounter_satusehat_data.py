# models/bronze/encounter_satusehat_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.fhir_resources.encounter_satusehat import fetch_encounter_satusehat

@model(
    "bronze.encounter_satusehat_data",
    kind=ModelKindName.FULL,
    columns={
        "name": "text",
        "owner": "text",
        "creation": "timestamp",
        "modified": "timestamp",
        "modified_by": "text",
        "docstatus": "int",
        "idx": "int",
        "patient_encounter": "text",
        "patient": "text",
        "patient_name": "text",
        "patient_ihs": "text",
        "practitioner": "text",
        "practitioner_name": "text",
        "practitioner_ihs": "text",
        "start_time": "timestamp",
        "organization_id": "text",
        "location_id": "text",
        "satusehat_id": "text",
        "status": "text",
        "api_response": "text",     # Next di parsing di silver model
        "payload_json": "text",     # Next di parsing di silver model
        "doctype": "text",
    },
)
def execute(context, start, end, execution_time, **kwargs) -> pd.DataFrame:
    with FrappeClient() as client:
        records = fetch_encounter_satusehat(client)
    return pd.DataFrame(records)