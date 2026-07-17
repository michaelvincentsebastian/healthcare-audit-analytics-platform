# models_dependencies/extractors/fhir_resources/condition_satusehat.py
from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import fetch_bulk


def fetch_condition_satusehat(client: FrappeClient, start=None, end=None) -> list[dict]:
    """Bulk fetch -- api_response & payload_json muncul sebagai text biasa
    (bukan child table), jadi ikut kebawa lewat fields=["*"] tanpa masalah."""
    settings = get_settings()
    return fetch_bulk(client, settings.condition_satusehat_endpoint, start=start, end=end)
