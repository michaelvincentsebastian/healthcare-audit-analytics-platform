# models_dependencies/config.py
#
# HANYA koneksi ke Frappe: base URL, credential, endpoint auth (login/session/
# logout). Endpoint per-resource (Patient, Encounter, *_SatuSehat, dst) BUKAN
# tanggung jawab file ini -- lihat constants.py.
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


def get_settings() -> FrappeConfig:
    load_dotenv()
    return FrappeConfig(
        base_url=os.getenv("API_BASE_URL"),
        login_user=os.getenv("API_LOGIN_USER"),
        login_password=os.getenv("API_LOGIN_PASSWORD"),
        login_endpoint=os.getenv("LOGIN_ENDPOINT"),
        session_endpoint=os.getenv("USER_SESSION_ENDPOINT"),
        logout_endpoint=os.getenv("LOGOUT_ENDPOINT"),
    )
