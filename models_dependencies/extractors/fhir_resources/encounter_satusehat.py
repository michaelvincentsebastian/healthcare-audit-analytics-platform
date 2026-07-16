from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import normalize


def fetch_encounter_satusehat(client: FrappeClient) -> list[dict]:
    settings = get_settings()
    res = client.get(settings.encounter_satusehat_endpoint)
    encounter_list = res.get("data", [])

    records = []
    for e in encounter_list:
        detail = client.get(f"{settings.encounter_satusehat_endpoint}/{e['name']}")["data"]
        records.append({key: normalize(value) for key, value in detail.items()})
    return records