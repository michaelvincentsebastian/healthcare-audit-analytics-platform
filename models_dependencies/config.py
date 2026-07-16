import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True)
class FrappeConfig:
    base_url: str
    login_user: str
    login_password: str
    login_endpoint: str
    session_endpoint: str
    logout_endpoint: str
    patient_endpoint: str
    practitioner_endpoint: str
    patient_encounter_endpoint: str
    encounter_satusehat_endpoint: str
    condition_satusehat_endpoint: str

def get_settings() -> FrappeConfig:
    load_dotenv()
    return FrappeConfig(
        base_url=os.getenv("API_BASE_URL"),
        login_user=os.getenv("API_LOGIN_USER"),
        login_password=os.getenv("API_LOGIN_PASSWORD"),
        login_endpoint=os.getenv("LOGIN_ENDPOINT"),
        session_endpoint=os.getenv("USER_SESSION_ENDPOINT"),
        logout_endpoint=os.getenv("LOGOUT_ENDPOINT"),
        patient_endpoint=os.getenv("PATIENT_ENDPOINT"),
        practitioner_endpoint=os.getenv("PRACTICIONER_ENDPOINT"),
        patient_encounter_endpoint=os.getenv("PATIENT_ENCOUNTER_ENDPOINT"),
        encounter_satusehat_endpoint=os.getenv("ENDCOUNTER_SATUSEHAT_ENDPOINT"),
        condition_satusehat_endpoint=os.getenv("CONDITION_SATUSEHAT_ENDPOINT")
    )