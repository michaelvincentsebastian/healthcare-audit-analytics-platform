# models_dependencies/utils.py
#
# Helper teknis generik yang tidak mengandung business logic dan tidak
# melakukan HTTP call. Transformasi data (flatten/normalize) ada di
# transformers/, dan fetch pattern (bulk / 1+N) ada di extractors/common.py.
from datetime import datetime

FRAPPE_DT_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_DETAIL_WORKERS = 5


def to_frappe_dt_str(value) -> str:
    """SQLMesh mengirim start/end ke execute() sebagai datetime/pendulum
    object, bukan str -- meski nama parameternya sering di-type-hint str.
    Harus diformat manual sebelum dipakai di filter Frappe / json.dumps()."""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime) or hasattr(value, "strftime"):
        return value.strftime(FRAPPE_DT_FORMAT)
    return str(value)
