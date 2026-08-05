# models_dependencies/transformers/normalize.py
#
# Transform murni (tidak ada HTTP call, tidak ada business branching):
# menyiapkan 1 nilai field Frappe supaya aman disimpan sebagai kolom flat
# di Bronze.
import json


def normalize(value):
    """Frappe child table (list) atau nested dict tidak bisa disimpan langsung
    sebagai kolom flat -- diserialize jadi JSON string supaya aman untuk Bronze."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    return value
