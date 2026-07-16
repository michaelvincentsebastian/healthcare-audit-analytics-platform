from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import normalize


def fetch_practitioners(client: FrappeClient) -> list[dict]:
    settings = get_settings()
    res = client.get(settings.practitioner_endpoint)
    practitioner_list = res.get("data", [])

    records = []
    for p in practitioner_list:
        detail = client.get(f"{settings.practitioner_endpoint}/{p['name']}")["data"]
        records.append({key: normalize(value) for key, value in detail.items()})
    return records