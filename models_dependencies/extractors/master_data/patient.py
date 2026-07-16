# models_dependencies/extractors/patient.py
import json

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import normalize, to_frappe_dt_str

# Semua field flat yang mau ditarik. HARUS sinkron dengan columns={} di
# models/bronze/master_data/patient_data.py, MINUS field child-table
# (patient_relation) -- child table tidak pernah ikut kebawa lewat
# frappe.client.get_list, jadi jangan dimasukkan di sini.
PATIENT_FIELDS = [
    "name", "owner", "creation", "modified", "modified_by", "docstatus",
    "idx", "naming_series", "first_name", "patient_name", "sex",
    "blood_group", "dob", "status", "uid", "satusehat_id",
    "inpatient_status", "report_preference", "invite_user", "user_id",
    "customer", "customer_group", "territory", "default_currency",
    "default_price_list", "language", "marital_status", "doctype",
]


def fetch_patients(client: FrappeClient, start=None, end=None) -> list[dict]:
    """1 bulk call, tanpa loop detail per record.

    start/end (kalau diisi) di-push jadi filter server-side ke Frappe
    berdasarkan kolom `modified` -- ini yang bikin INCREMENTAL_BY_TIME_RANGE
    nanti beneran cuma narik delta, bukan full table tiap batch.
    """
    settings = get_settings()

    params = {
        "fields": json.dumps(PATIENT_FIELDS),
        "limit_page_length": 0,  # 0 = unlimited, jangan andalkan default 20
    }
    if start and end:
        start_str = to_frappe_dt_str(start)
        end_str = to_frappe_dt_str(end)
        params["filters"] = json.dumps([["modified", "between", [start_str, end_str]]])

    res = client.get(settings.patient_endpoint, params=params)
    patient_list = res.get("data", [])

    return [{key: normalize(value) for key, value in row.items()} for row in patient_list]