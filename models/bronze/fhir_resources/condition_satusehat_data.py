# models/bronze/fhir_resources/condition_satusehat_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.fhir_resources.condition_satusehat import fetch_condition_satusehat

@model(
    "bronze.condition_satusehat_data",
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
        "encounter_satusehat": "TEXT",
        "patient_encounter": "TEXT",
        "patient": "TEXT",
        "patient_name": "TEXT",
        "patient_ihs": "TEXT",
        "satusehat_encounter_id": "TEXT",
        "icd_code": "TEXT",
        "diagnosis_display": "TEXT",
        "validation_status": "TEXT",
        "satusehat_id": "TEXT",
        "api_response": "TEXT",   # Di-parse di Silver model
        "payload_json": "TEXT",   # Di-parse di Silver model
    },
)
def execute(context, start, end, execution_time, **kwargs):
    with FrappeClient() as client:
        records = fetch_condition_satusehat(client, start=start, end=end)

    if not records:
        yield from ()
        return

    yield pd.DataFrame(records)
