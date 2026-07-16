from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from models_dependencies.clients.frappe_client import FrappeClient
from models_dependencies.config import get_settings
from models_dependencies.utils import normalize, to_frappe_dt_str

MAX_WORKERS = 15  # sesuaikan dengan kapasitas server Frappe -- jangan asal gedein


def fetch_patient_encounters(
    client: FrappeClient,
    start=None,
    end=None,
    max_workers: int = MAX_WORKERS,
) -> list[dict]:
    """Bulk list call (murah, 1 request) lalu detail call diparalel.

    Detail call tetap perlu per-record karena patient_encounter punya
    banyak child table (diagnosis, symptoms, drug_prescription, dst) yang
    cuma muncul di endpoint detail, bukan di list. Yang dioptimasi di sini
    cuma wall-time-nya lewat concurrency, bukan jumlah request totalnya.
    """
    settings = get_settings()

    params = {"limit_page_length": 0}
    if start and end:
        start_str = to_frappe_dt_str(start)
        end_str = to_frappe_dt_str(end)
        params["filters"] = json.dumps([["modified", "between", [start_str, end_str]]])

    res = client.get(settings.patient_encounter_endpoint, params=params)
    encounter_list = res.get("data", [])

    def _fetch_detail(e: dict) -> dict:
        detail = client.get(f"{settings.patient_encounter_endpoint}/{e['name']}")["data"]
        return {key: normalize(value) for key, value in detail.items()}

    records = []
    errors = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_detail, e): e["name"] for e in encounter_list}
        for future in as_completed(futures):
            name = futures[future]
            try:
                records.append(future.result())
            except Exception as exc:
                # jangan biarkan 1 record gagal menjatuhkan seluruh batch --
                # catat, lanjut, laporkan di akhir supaya kelihatan di log run.
                errors.append((name, str(exc)))

    if errors:
        print(f"[fetch_patient_encounters] {len(errors)} record gagal ditarik: {errors[:5]}"
              + (" ..." if len(errors) > 5 else ""))

    return records