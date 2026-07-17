# models/bronze/patient_data.py

import pandas as pd

from sqlmesh import model
from sqlmesh.core.model import ModelKindName

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.extractors.master_data.patient import fetch_patients


@model(
    "bronze.patient_data",
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
        "patient_name": "TEXT",
        "sex": "TEXT",
        "blood_group": "TEXT",
        "dob": "DATE",
        "image": "TEXT",
        "status": "TEXT",
        "uid": "TEXT",
        "satusehat_id": "TEXT",
        "inpatient_record": "TEXT",
        "inpatient_status": "TEXT",
        "report_preference": "TEXT",
        "mobile": "TEXT",
        "phone": "TEXT",
        "email": "TEXT",
        "invite_user": "INT",
        "user_id": "TEXT",
        "customer": "TEXT",
        "customer_group": "TEXT",
        "territory": "TEXT",
        "default_currency": "TEXT",
        "default_price_list": "TEXT",
        "language": "TEXT",
        "patient_details": "TEXT",
        "occupation": "TEXT",
        "marital_status": "TEXT",
        "allergies": "TEXT",
        "medication": "TEXT",
        "medical_history": "TEXT",
        "surgical_history": "TEXT",
        "tobacco_past_use": "TEXT",
        "tobacco_current_use": "TEXT",
        "alcohol_past_use": "TEXT",
        "alcohol_current_use": "TEXT",
        "surrounding_factors": "TEXT",
        "other_risk_factors": "TEXT",
        "satusehat_resource_id": "TEXT",
        "fhir_status": "TEXT",
        "satusehat_resource_type": "TEXT",
    },
)
def execute(context, start, end, execution_time, **kwargs):
    with FrappeClient() as client:
        records = fetch_patients(client, start=start, end=end)

    # Interval incremental yang genuinely tidak ada data (hari sepi, dsb)
    # itu KONDISI NORMAL, bukan kegagalan -- jangan sampai bikin whole plan
    # gagal. `pd.DataFrame([])` menghasilkan 0 kolom (bukan 0 baris dengan
    # skema tetap ada), jadi SQLMesh gak bisa construct INSERT query dari
    # situ. Solusinya: kalau kosong, jangan yield apa-apa sama sekali --
    # sesuai rekomendasi resmi SQLMesh.
    if not records:
        yield from ()
        return

    df = pd.DataFrame(records)

    yield df