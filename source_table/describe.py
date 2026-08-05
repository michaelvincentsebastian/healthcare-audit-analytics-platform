"""
Introspeksi skema (nama kolom + tipe data) untuk semua tabel whitelist
di bridge Quack. Hasilnya dipakai untuk rebuild model Bronze SQLMesh
dengan kolom eksplisit (bukan SELECT *) -- supaya:
  1. Tidak kena linter error `invalidselectstarexpansion` dari SQLMesh
  2. Tidak perlu jalankan `sqlmesh create_external_models` tiap ada
     perubahan skema di MariaDB (karena tidak bergantung external_models.yaml)

Jalankan dari root project lakehouse:
    python describe_bridge_schema.py

Butuh .env dengan QUACK_URI, QUACK_SERVING_TOKEN, QUACK_DISABLE_SSL
(nama key sama seperti yang dipakai macros/quack_bridge.py).
"""
import json
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

# --- Load .env dari root project (cari mulai dari cwd naik ke atas) ---
for parent in [Path.cwd(), *Path.cwd().resolve().parents]:
    candidate = parent / ".env"
    if candidate.exists():
        load_dotenv(candidate)
        break

QUACK_URI = "quack:localhost:9494"
QUACK_TOKEN = os.environ["QUACK_SOURCE_TOKEN"]
QUACK_DISABLE_SSL = "true"

# model SQLMesh (folder/nama file) -> nama view di schema `bridge`
# (harus konsisten dengan whitelisted_tables di analytics-bridge/serve.py)
MODEL_TO_VIEW = {
    "master_data/item_data": "tabitem",
    "master_data/patient_data": "tabpatient",
    "master_data/practitioner_data": "tabhealthcare_practitioner",
    "encounter/patient_encounter_data": "tabpatient_encounter",
    "send_to_satusehat/allergy_intolerance_satusehat_data": "taballergyintolerance_satusehat",
    "send_to_satusehat/careplan_satusehat_data": "tabcareplan_satusehat",
    "send_to_satusehat/composition_satusehat_data": "tabcomposition_satusehat",
    "send_to_satusehat/condition_satusehat_data": "tabcondition_satusehat",
    "send_to_satusehat/diagnostic_report_satusehat_data": "tabdiagnosticreport_satusehat",
    "send_to_satusehat/encounter_satusehat_data": "tabencounter_satusehat",
    "send_to_satusehat/episode_of_care_satusehat_data": "tabepisodeofcare_satusehat",
    "send_to_satusehat/imaging_study_satusehat_data": "tabimagingstudy_satusehat",
    "send_to_satusehat/immunization_satusehat_data": "tabimmunization_satusehat",
    "send_to_satusehat/medication_dispense_satusehat_data": "tabmedicationdispense_satusehat",
    "send_to_satusehat/medication_statement_satusehat_data": "tabmedicationstatement_satusehat",
    "send_to_satusehat/observation_satusehat_data": "tabobservation_satusehat",
    "send_to_satusehat/procedure_satusehat_data": "tabprocedure_satusehat",
    "send_to_satusehat/questionnaire_response_satusehat_data": "tabquestionnaireresponse_satusehat",
    "send_to_satusehat/service_request_satusehat_data": "tabservicerequest_satusehat",
    "send_to_satusehat/specimen_satusehat_data": "tabspecimen_satusehat",
}


def main():
    con = duckdb.connect()
    con.execute("INSTALL quack; LOAD quack;")
    print("BERHASIL INSTALL LOAD QUACK")
    con.execute(f"""
        ATTACH '{QUACK_URI}' AS frappe_bridge (
            TOKEN '{QUACK_TOKEN}'
        )
    """)
    print("BERHASIL CONNECT KE QUACK BRIDGE")

    schema_dump = {}
    failed = []

    for model_name, view in MODEL_TO_VIEW.items():
        try:
            # NOTE: sengaja pakai DESCRIBE, bukan COUNT(*) -- COUNT(*) di
            # atas view yang men-scan tabel via mysql extension memicu bug
            # internal DuckDB (lihat catatan di serve.py bridge). DESCRIBE
            # cuma baca metadata katalog, tidak menjalankan aggregate scan,
            # jadi aman dari bug itu.
            rows = con.execute(f'DESCRIBE frappe_bridge.bridge."{view}"').fetchall()
            columns = [{"name": r[0], "type": r[1]} for r in rows]
            schema_dump[model_name] = {"view": view, "columns": columns}
            print(f"OK    {model_name:55s} <- {view} ({len(columns)} kolom)")
        except Exception as e:
            failed.append((model_name, view, str(e)))
            print(f"GAGAL {model_name:55s} <- {view}: {e}")

    out_path = Path("source_table/bronze_schema_dump.json")
    out_path.write_text(json.dumps(schema_dump, indent=2))
    print(f"\nSelesai. {len(schema_dump)}/{len(MODEL_TO_VIEW)} tabel berhasil.")
    print(f"Skema tersimpan di: {out_path.resolve()}")

    if failed:
        print("\nTabel yang GAGAL di-describe (perlu dicek manual):")
        for model_name, view, err in failed:
            print(f"  - {model_name} ({view}): {err}")


if __name__ == "__main__":
    main()