from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import normalize


def fetch_condition_satusehat(client: FrappeClient) -> list[dict]:
    settings = get_settings()
    res = client.get(settings.condition_satusehat_endpoint)
    condition_list = res.get("data", [])

    records = []
    for c in condition_list:
        detail = client.get(f"{settings.condition_satusehat_endpoint}/{c['name']}")["data"]
        records.append({key: normalize(value) for key, value in detail.items()})
    return records