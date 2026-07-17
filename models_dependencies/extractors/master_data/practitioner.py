# models_dependencies/extractors/master_data/practitioner.py
from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import fetch_bulk


def fetch_practitioners(client: FrappeClient, start=None, end=None) -> list[dict]:
    """Bulk fetch -- terbukti fields=["*"] untuk Practitioner tidak
    menyertakan child table (practitioner_schedules, accounts), jadi aman
    full-bulk tanpa detail call sama sekali."""
    settings = get_settings()
    return fetch_bulk(client, settings.practitioner_endpoint, start=start, end=end)
