import json
from datetime import datetime

FRAPPE_DT_FORMAT = "%Y-%m-%d %H:%M:%S"


def normalize(value):
    """Frappe child table (list) atau nested dict tidak bisa disimpan langsung
    sebagai kolom flat — diserialize jadi JSON string supaya aman untuk Bronze."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    return value


def to_frappe_dt_str(value) -> str:
    """SQLMesh mengirim start/end ke execute() sebagai datetime/pendulum
    object, bukan str -- meski nama parameternya sering di-type-hint str.
    Harus diformat manual sebelum dipakai di filter Frappe / json.dumps()."""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime) or hasattr(value, "strftime"):
        return value.strftime(FRAPPE_DT_FORMAT)
    return str(value)