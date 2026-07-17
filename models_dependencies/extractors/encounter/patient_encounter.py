# models_dependencies/extractors/encounter/patient_encounter.py
from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import fetch_bulk


def fetch_patient_encounters(client: FrappeClient, start=None, end=None) -> list[dict]:
    """Bulk fetch -- terbukti fields=["*"] untuk Patient Encounter TIDAK
    menyertakan child table (diagnosis, symptoms, drug_prescription, dst),
    lihat list_output_bulk_all.txt. Threaded detail-call per record yang
    dipakai sebelumnya sudah tidak diperlukan lagi."""
    settings = get_settings()
    return fetch_bulk(client, settings.patient_encounter_endpoint, start=start, end=end)
