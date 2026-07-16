import requests
from requests.adapters import HTTPAdapter
from models_dependencies.config import get_settings

class FrappeClient:
    """Handles login, session, logout. No knowledge of specific resources."""

    def __init__(self, config=None, pool_maxsize: int = 20):
        self.cfg = config or get_settings()
        self.session = requests.Session()
        # Default requests pool cuma 10 koneksi -- kalau dipakai bareng
        # ThreadPoolExecutor dengan banyak worker, connection pool jadi
        # bottleneck baru. Naikkan sesuai max_workers yang dipakai.
        adapter = HTTPAdapter(pool_connections=pool_maxsize, pool_maxsize=pool_maxsize)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()

    def login(self):
        resp = self.session.post(
            f"{self.cfg.base_url}{self.cfg.login_endpoint}",
            json={"usr": self.cfg.login_user, "pwd": self.cfg.login_password},
        )
        resp.raise_for_status()

    def logout(self):
        try:
            self.session.post(f"{self.cfg.base_url}{self.cfg.logout_endpoint}")
        except requests.RequestException:
            pass  # jangan sampai logout gagal ganggu pipeline

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        resp = self.session.get(f"{self.cfg.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()