# Lakehouse

---

## Prerequisites

[V] Python 3.10, 3.11, or 3.12
[V] Docker installed & running
[]


---

## Project Root

```text

```

---

## Initial Setup

1. virtual environment init & run
`python3 -m venv .venv` 
`source .venv/bin/activate`

2. Install all needed depedencies (requirements.txt)
`python3 -m pip install -r requirements.txt`


3. Run docker compose up (host minio & postgres services on local machine)
`docker compose up -d`

4. Run `lakehouse-setup.py` for building lakehouse architecture.
- Choose 9 for full initial setup.

5. SQLMesh Project Initiation
```text
- Run `sqlmesh init`
1. What type of project do you want to set up?
- [3]
2. Choose your SQL engine:
- [1]
3. Choose your SQLMesh CLI experience:
- [1]
```

6. 

---

## FLOW Transformasi FHIR

1. Extract & ambil value `payload_json` dari setiap endpoint FHIR resources (`/send satusehat` API docs).
2. Masukan di dir `flatquack/input/` sebagai `[resources_name].txt`.
3. Rancang ViewDefinition dari FHIR resources di `flatquack/views/` (supaya flatquack bisa buat SQL Query untuk flatten ndjson fhir nya).
4. Jalankan program python.
5. Ambil SQL Query di `flatquack/output/flatten_query.sql`.
6. Ambil SQL Query tersebut, sesuaikan supaya bisa di baca oleh `SQLMesh + DuckDB` (LLM), lalu paste ke resources yang sesuai (di silver layer).
7. Jalankan SQLMesh Plan


| Note: Disini jika format FHIR berubah dan ingin ingest perubahan itu juga, maka harus rancang ulang/update ViewDefinition. Karena flatquack bukan tools otomatis yang bisa detect perubahan.