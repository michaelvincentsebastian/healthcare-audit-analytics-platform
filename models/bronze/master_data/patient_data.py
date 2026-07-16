# models/bronze/patient_data.py

import pandas as pd

from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.master_data.patient import fetch_patients


@model(
    "bronze.patient_data",
    kind=ModelKindName.FULL,
    columns={
        "name": "TEXT",
        "owner": "TEXT",
        "creation": "TIMESTAMP",
        "modified": "TIMESTAMP",
        "modified_by": "TEXT",
        "docstatus": "INT",
        "idx": "INT",
        "naming_series": "TEXT",
        "first_name": "TEXT",
        "patient_name": "TEXT",
        "sex": "TEXT",
        "blood_group": "TEXT",
        "dob": "DATE",
        "status": "TEXT",
        "uid": "BIGINT",
        "satusehat_id": "TEXT",
        "inpatient_status": "TEXT",
        "report_preference": "TEXT",
        "invite_user": "INT",
        "user_id": "TEXT",
        "customer": "TEXT",
        "customer_group": "TEXT",
        "territory": "TEXT",
        "default_currency": "TEXT",
        "default_price_list": "TEXT",
        "language": "TEXT",
        "marital_status": "TEXT",
        "doctype": "TEXT",
        "patient_relation": "JSON"
    },
)
def execute(context, start, end, execution_time, **kwargs) -> pd.DataFrame:
    with FrappeClient() as client:
        records = fetch_patients(client)

    return pd.DataFrame(records)