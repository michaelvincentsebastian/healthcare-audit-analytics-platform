# models/bronze/master_data/practitioner_data.py
import pandas as pd
from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.master_data.practitioner import fetch_practitioners

@model(
    "bronze.practitioner_data",
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
        "first_name": "TEXT",
        "middle_name": "TEXT",
        "last_name": "TEXT",
        "practitioner_name": "TEXT",
        "nik": "TEXT",
        "satusehat_id": "TEXT",
        "gender": "TEXT",
        "image": "TEXT",
        "status": "TEXT",
        "mobile_phone": "TEXT",
        "residence_phone": "TEXT",
        "office_phone": "TEXT",
        "practitioner_type": "TEXT",
        "employee": "TEXT",
        "supplier": "TEXT",
        "department": "TEXT",
        "designation": "TEXT",
        "user_id": "TEXT",
        "hospital": "TEXT",
        "google_calendar": "TEXT",
        "op_consulting_charge_item": "TEXT",
        "op_consulting_charge": "DOUBLE",
        "inpatient_visit_charge_item": "TEXT",
        "inpatient_visit_charge": "DOUBLE",
        "default_currency": "TEXT",
        "practitioner_primary_contact": "TEXT",
        "mobile_no": "TEXT",
        "email_id": "TEXT",
        "practitioner_primary_address": "TEXT",
        "primary_address": "TEXT",
        "satusehat_resource_id": "TEXT",
        "fhir_status": "TEXT",
        "satusehat_resource_type": "TEXT",
    },
)
def execute(context, start, end, execution_time, **kwargs):
    with FrappeClient() as client:
        records = fetch_practitioners(client, start=start, end=end)

    # Interval tanpa data baru itu normal untuk incremental -- jangan
    # sampai bikin plan gagal (lihat catatan sama di patient_data.py).
    if not records:
        yield from ()
        return

    yield pd.DataFrame(records)
