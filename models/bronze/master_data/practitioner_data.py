# models/bronze/practitioner_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.master_data.practitioner import fetch_practitioners

@model(
    "bronze.practitioner_data",
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
        "first_name": "text",
        "practitioner_name": "text",
        "nik": "text",
        "satusehat_id": "text",
        "status": "text",
        "practitioner_type": "text",
        "op_consulting_charge": "double",
        "inpatient_visit_charge": "double",
        "default_currency": "text",
        "mobile_no": "text",
        "email_id": "text",
        "doctype": "text",
        "practitioner_schedules": "json",
        "accounts": "json",
    },
)
def execute(context, start, end, execution_time, **kwargs) -> pd.DataFrame:
    with FrappeClient() as client:
        records = fetch_practitioners(client)
    return pd.DataFrame(records)