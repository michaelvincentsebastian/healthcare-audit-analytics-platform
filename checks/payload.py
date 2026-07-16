import os
from dotenv import load_dotenv
import requests
import duckdb

load_dotenv()

# --- Konfigurasi API Endpoint ---

## Access & Authentication Endpoinnt
BASE = os.getenv("API_BASE_URL")
USER_LOGIN = os.getenv("API_LOGIN_USER")
PASSWORD_LOGIN = os.getenv("API_LOGIN_PASSWORD")
LOGIN_ENDPOINT = os.getenv("LOGIN_ENDPOINT")
USER_SESSION_ENDPOINT = os.getenv("USER_SESSION_ENDPOINT")
LOGOUT_ENDPOINT = os.getenv("LOGOUT_ENDPOINT")

## Data Endpoint
PATIENT_ENDPOINT = os.getenv("PATIENT_ENDPOINT")
PRACTICIONER_ENDPOINT = os.getenv("PRACTICIONER_ENDPOINT")
ENDCOUNTER_SATUSEHAT_ENDPOINT = os.getenv("ENDCOUNTER_SATUSEHAT_ENDPOINT")
PATIENT_ENCOUNTER_ENDPOINT = os.getenv("PATIENT_ENCOUNTER_ENDPOINT")

try:
    # Koneksi ke DuckDB
    con = duckdb.connect()

    # Gunakan session agar Cookie (`sid`) otomatis disimpan dan dikirim kembali
    session = requests.Session()
    
    # Show User Login Credentaials
    payload = {
        "usr": USER_LOGIN,
        "pwd": PASSWORD_LOGIN
    }
    print(f"user: {payload['usr']}, password: {payload['pwd']}")
    
    # --- 1. PROSES LOGIN ---
    login = session.post(
        f"{BASE}{LOGIN_ENDPOINT}",
        json={
            "usr": USER_LOGIN,
            "pwd": PASSWORD_LOGIN
        }
    )
    login.raise_for_status() 
    print("Login Sukses! Respons:", login.json())
    
    # --- 2. CEK SESSION USER ---
    check_session = session.get(f"{BASE}{USER_SESSION_ENDPOINT}")
    check_session.raise_for_status()
    print("Session User saat ini:", check_session.json())
    
    # # --- 3. GET PATIENT DATA ---
    # get_patient = session.get(f"{BASE}{PATIENT_ENDPOINT}")
    # get_patient.raise_for_status()
    
    # res_json = get_patient.json()
    
    # patient_data = res_json.get("data")
    # print("Patient List Response:", patient_data)
    
    # for patient_detail in patient_data:
    #     print(" => Data Pasien:", patient_detail['name'])
        
    #     patient_detail_response = session.get(
    #         f"{BASE}{PATIENT_ENDPOINT}/{patient_detail['name']}")
        
    #     patient_detail_formated = patient_detail_response.json()["data"]
        
    #     print(f"\nSchema untuk pasien: {patient_detail_formated['name']}")
    #     print("-" * 50)

    #     for key, value in patient_detail_formated.items():
    #         print(f"{key}: {type(value).__name__}")
        
        # patient_name = patient_detail_formated["name"]
        # patient_uid = patient_detail_formated["uid"]
        # patient_dob = patient_detail_formated["dob"]
        # patient_sex = patient_detail_formated["sex"]
        # patient_status = patient_detail_formated["status"]
        
        # print(" - Nama:", patient_name)
        # print(" - UID:", patient_uid)
        # print(" - Tanggal Lahir:", patient_dob)
        # print(" - Jenis Kelamin:", patient_sex)
        # print(" - Status:", patient_status)
    
    # # --- 4. GET PRACTITIONER DATA ---
    # get_practicioner = session.get(f"{BASE}{PRACTICIONER_ENDPOINT}")
    # get_practicioner.raise_for_status()
    
    # get_practicioner_data = get_practicioner.json().get("data")
    # print(f"List Practicioner:\n{get_practicioner_data}")
    
    # for practicioner in get_practicioner_data:
    #     practicioner_id = practicioner["name"]
    #     print(f"Fetching Details for Practicioner ID: {practicioner_id}")
        
    #     practicioner_details = session.get(
    #         f'{BASE}{PRACTICIONER_ENDPOINT}/{practicioner_id}'
    #     )
    #     practicioner_details.raise_for_status()
        
    #     practicioner_detail_formated = practicioner_details.json().get("data")
        
    #     for key, value in practicioner_detail_formated.items():
    #         print(f"{key}: {type(value).__name__}")    
    
    
    # # --- 5. GET PATIENT ENCOUNTER (Janji Temu Pasien dengan Dokter) ---
    get_patient_encounter = session.get(f"{BASE}{PATIENT_ENCOUNTER_ENDPOINT}")
    get_patient_encounter.raise_for_status()
    
    get_patient_encounter_data = get_patient_encounter.json().get("data")
    print(f"List Practicioner:\n{get_patient_encounter_data}")
    
    for patient_encounter in get_patient_encounter_data:
        patient_encounter_id = patient_encounter["name"]
        print(f"Fetching Details for Patient Encounter ID: {patient_encounter_id}")
        
        patient_encounter_details = session.get(
            f'{BASE}{PATIENT_ENCOUNTER_ENDPOINT}/{patient_encounter_id}'
        )
        patient_encounter_details.raise_for_status()
        
        patient_encounter_details_formated = patient_encounter_details.json().get("data")
        
        for key, value in patient_encounter_details_formated.items():
            print(f"{key}: {value}")
    
    # # --- 6. GET FHIR RESOURCES ---
    
    # get_encounter = session.get(f"{BASE}{ENDCOUNTER_SATUSEHAT_ENDPOINT}")
    # get_encounter.raise_for_status()
    
    # get_encounter_data = get_encounter.json().get("data")
    # print("Encounter List Response:", get_encounter_data) 
    
    # for encounter in get_encounter_data:
    #     encounter_id = encounter['name']
    #     print(f"Fetching FHIR resources for Encounter ID: {encounter_id}")
        
    #     fhir_resources = session.get(
    #         f'{BASE}{ENDCOUNTER_SATUSEHAT_ENDPOINT}/?fields=["name","payload_json"]&filters=[["name","=","ENC-SS-2026-07-0004"]]'
    #     )
    #     fhir_resources.raise_for_status()
        
    #     fhir_resources_data = fhir_resources.json().get("data")
    #     print(f"FHIR Resources for Encounter ID {encounter_id}:", fhir_resources_data)

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP Error terjadi: {http_err}")
    
    # Jika error, intip respons dari server
    if 'get_patient' in locals():
        print("Isi error detail:", get_patient.text)
    
    elif 'login' in locals():
        print("Isi error login:", login.text)

except ValueError as val_err:
    print(f"Gagal membaca JSON: {val_err}")

except Exception as e:
    print("Terjadi kesalahan sistem:", e)
    
finally:
    if 'con' in locals():
        con.close()
        
    requests.post(f"{BASE}{LOGOUT_ENDPOINT}")
    
    print("Logout berhasil, sesi berakhir.")