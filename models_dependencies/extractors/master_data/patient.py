# models_dependencies/extractors/patient.py

import json

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import normalize, to_frappe_dt_str


def fetch_patients(client: FrappeClient, start=None, end=None) -> list[dict]:
    """
    Bulk extraction menggunakan fields=["*"].

    Schema tabel tetap dikontrol oleh SQLMesh (patient_data.py).
    """

    settings = get_settings()

    params = {
        "fields": json.dumps(["*"]),
        "limit_page_length": 0,
    }

    if start and end:
        start_str = to_frappe_dt_str(start)
        end_str = to_frappe_dt_str(end)

        params["filters"] = json.dumps([
            ["modified", "between", [start_str, end_str]]
        ])

    response = client.get(settings.patient_endpoint, params=params)

    patient_list = response.get("data", [])

    return [
        {
            key: normalize(value)
            for key, value in row.items()
        }
        for row in patient_list
    ]