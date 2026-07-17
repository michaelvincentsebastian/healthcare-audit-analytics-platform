# models/bronze/fhir_resources/encounter_satusehat_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.fhir_resources.encounter_satusehat import fetch_encounter_satusehat

@model(
    "bronze.encounter_satusehat_data",
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
        "patient_encounter": "TEXT",
        "patient": "TEXT",
        "patient_name": "TEXT",
        "patient_ihs": "TEXT",
        "practitioner": "TEXT",
        "practitioner_name": "TEXT",
        "practitioner_ihs": "TEXT",
        "start_time": "TIMESTAMP",
        "organization_id": "TEXT",
        "location_id": "TEXT",
        "satusehat_id": "TEXT",
        "status": "TEXT",
        "api_response": "TEXT",   # Di-parse di Silver model
        "payload_json": "TEXT",   # Di-parse di Silver model
    },
)
def execute(context, start, end, execution_time, **kwargs):
    with FrappeClient() as client:
        records = fetch_encounter_satusehat(client, start=start, end=end)

    if not records:
        yield from ()
        return

    yield pd.DataFrame(records)
